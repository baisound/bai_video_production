#include "bai_obs_capture/ipc_client.hpp"

#include <algorithm>
#include <array>
#include <chrono>
#include <cstddef>
#include <cstring>
#include <vector>

#ifdef _WIN32
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <Windows.h>
#include <bcrypt.h>
#endif

namespace bai::obs_capture {
namespace {

#ifdef _WIN32
bool write_exact(HANDLE pipe, const void *data, std::uint32_t bytes) noexcept {
  const auto *cursor = static_cast<const std::uint8_t *>(data);
  std::uint32_t remaining = bytes;
  while (remaining > 0) {
    DWORD written = 0;
    if (!WriteFile(pipe, cursor, remaining, &written, nullptr) || written == 0) return false;
    cursor += written;
    remaining -= written;
  }
  return true;
}

bool same_user_as_server(HANDLE pipe) noexcept {
  ULONG server_pid = 0;
  if (!GetNamedPipeServerProcessId(pipe, &server_pid) || server_pid == 0) return false;
  HANDLE server = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, server_pid);
  if (server == nullptr) return false;
  HANDLE server_token = nullptr;
  HANDLE current_token = nullptr;
  bool equal = false;
  if (OpenProcessToken(server, TOKEN_QUERY, &server_token) &&
      OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &current_token)) {
    DWORD server_bytes = 0;
    DWORD current_bytes = 0;
    GetTokenInformation(server_token, TokenUser, nullptr, 0, &server_bytes);
    GetTokenInformation(current_token, TokenUser, nullptr, 0, &current_bytes);
    if (server_bytes > 0 && current_bytes > 0) {
      std::vector<std::uint8_t> server_user(server_bytes);
      std::vector<std::uint8_t> current_user(current_bytes);
      if (GetTokenInformation(server_token, TokenUser, server_user.data(), server_bytes,
                              &server_bytes) &&
          GetTokenInformation(current_token, TokenUser, current_user.data(), current_bytes,
                              &current_bytes)) {
        const auto *left = reinterpret_cast<const TOKEN_USER *>(server_user.data());
        const auto *right = reinterpret_cast<const TOKEN_USER *>(current_user.data());
        equal = EqualSid(left->User.Sid, right->User.Sid) != FALSE;
      }
      std::fill(server_user.begin(), server_user.end(), std::uint8_t{0});
      std::fill(current_user.begin(), current_user.end(), std::uint8_t{0});
    }
  }
  if (current_token != nullptr) CloseHandle(current_token);
  if (server_token != nullptr) CloseHandle(server_token);
  CloseHandle(server);
  return equal;
}

bool read_session_hello(HANDLE pipe, const std::atomic<bool> &stop_requested,
                        SessionKey &key) noexcept {
  SessionHello hello{};
  auto *cursor = reinterpret_cast<std::uint8_t *>(&hello);
  DWORD offset = 0;
  const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(5);
  while (offset < sizeof(hello) && !stop_requested.load(std::memory_order_acquire)) {
    DWORD available = 0;
    if (!PeekNamedPipe(pipe, nullptr, 0, nullptr, &available, nullptr)) return false;
    if (available == 0) {
      if (std::chrono::steady_clock::now() >= deadline) return false;
      std::this_thread::sleep_for(std::chrono::milliseconds(10));
      continue;
    }
    DWORD received = 0;
    const DWORD wanted = static_cast<DWORD>(sizeof(hello) - offset);
    if (!ReadFile(pipe, cursor + offset, wanted, &received, nullptr) || received == 0) return false;
    offset += received;
  }
  if (offset != sizeof(hello) || hello.magic != kSessionHelloMagic ||
      hello.version != kSessionHelloVersion || hello.header_bytes != sizeof(hello) ||
      std::all_of(hello.session_key.begin(), hello.session_key.end(),
                  [](std::uint8_t value) { return value == 0; })) {
    std::fill(reinterpret_cast<std::uint8_t *>(&hello),
              reinterpret_cast<std::uint8_t *>(&hello) + sizeof(hello), std::uint8_t{0});
    return false;
  }
  key = hello.session_key;
  std::fill(reinterpret_cast<std::uint8_t *>(&hello),
            reinterpret_cast<std::uint8_t *>(&hello) + sizeof(hello), std::uint8_t{0});
  return true;
}

bool compute_hmac(const SessionKey &key, const WireHeader &header, const AudioFrame &frame,
                  std::array<std::uint8_t, kMacBytes> &out) noexcept {
  BCRYPT_ALG_HANDLE algorithm = nullptr;
  BCRYPT_HASH_HANDLE hash = nullptr;
  DWORD object_bytes = 0;
  DWORD returned = 0;
  std::array<std::uint8_t, 512> object{};
  bool ok = false;

  if (BCryptOpenAlgorithmProvider(&algorithm, BCRYPT_SHA256_ALGORITHM, nullptr,
                                  BCRYPT_ALG_HANDLE_HMAC_FLAG) < 0)
    goto cleanup;
  if (BCryptGetProperty(algorithm, BCRYPT_OBJECT_LENGTH,
                        reinterpret_cast<PUCHAR>(&object_bytes), sizeof(object_bytes),
                        &returned, 0) < 0 || object_bytes > object.size())
    goto cleanup;
  if (BCryptCreateHash(algorithm, &hash, object.data(), object_bytes,
                       const_cast<PUCHAR>(key.data()), static_cast<ULONG>(key.size()), 0) < 0)
    goto cleanup;

  if (BCryptHashData(hash, reinterpret_cast<PUCHAR>(const_cast<WireHeader *>(&header)),
                     static_cast<ULONG>(offsetof(WireHeader, hmac_sha256)), 0) < 0)
    goto cleanup;
  if (BCryptHashData(hash, reinterpret_cast<PUCHAR>(const_cast<float *>(frame.samples.data())),
                     header.payload_bytes, 0) < 0)
    goto cleanup;
  if (BCryptFinishHash(hash, out.data(), static_cast<ULONG>(out.size()), 0) < 0) goto cleanup;
  ok = true;

cleanup:
  if (hash != nullptr) BCryptDestroyHash(hash);
  if (algorithm != nullptr) BCryptCloseAlgorithmProvider(algorithm, 0);
  std::fill(object.begin(), object.end(), std::uint8_t{0});
  return ok;
}
#endif

}  // namespace

IpcClient::IpcClient(CaptureCore &core, const wchar_t *pipe_name)
    : core_(core), pipe_name_(pipe_name == nullptr ? kPipeName : pipe_name) {}

IpcClient::~IpcClient() {
  stop();
  std::fill(nonce_.begin(), nonce_.end(), std::uint8_t{0});
}

bool IpcClient::start() {
  bool expected = false;
  if (!running_.compare_exchange_strong(expected, true, std::memory_order_acq_rel)) return false;
#ifdef _WIN32
  if (BCryptGenRandom(nullptr, nonce_.data(), static_cast<ULONG>(nonce_.size()),
                      BCRYPT_USE_SYSTEM_PREFERRED_RNG) < 0) {
    running_.store(false, std::memory_order_release);
    return false;
  }
#else
  running_.store(false, std::memory_order_release);
  return false;
#endif
  stop_requested_.store(false, std::memory_order_release);
  worker_ = std::thread(&IpcClient::worker_main, this);
  return true;
}

void IpcClient::stop() noexcept {
  stop_requested_.store(true, std::memory_order_release);
  if (worker_.joinable()) worker_.join();
  running_.store(false, std::memory_order_release);
}

bool IpcClient::running() const noexcept { return running_.load(std::memory_order_acquire); }

std::uint64_t IpcClient::sent_frames() const noexcept {
  return sent_frames_.load(std::memory_order_relaxed);
}

std::uint64_t IpcClient::transport_drops() const noexcept {
  return transport_drops_.load(std::memory_order_relaxed);
}

std::uint64_t IpcClient::handshake_failures() const noexcept {
  return handshake_failures_.load(std::memory_order_relaxed);
}

void IpcClient::worker_main() noexcept {
#ifdef _WIN32
  HANDLE pipe = INVALID_HANDLE_VALUE;
  std::uint64_t sequence = 0;
  AudioFrame frame{};
  SessionKey key{};
  core_.set_authorized(false);

  while (!stop_requested_.load(std::memory_order_acquire)) {
    if (pipe == INVALID_HANDLE_VALUE) {
      pipe = CreateFileW(pipe_name_.c_str(), GENERIC_READ | GENERIC_WRITE, 0, nullptr, OPEN_EXISTING,
                         FILE_ATTRIBUTE_NORMAL, nullptr);
      if (pipe == INVALID_HANDLE_VALUE) {
        core_.set_authorized(false);
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
        continue;
      }
      if (!same_user_as_server(pipe) || !read_session_hello(pipe, stop_requested_, key)) {
        handshake_failures_.fetch_add(1, std::memory_order_relaxed);
        std::fill(key.begin(), key.end(), std::uint8_t{0});
        CloseHandle(pipe);
        pipe = INVALID_HANDLE_VALUE;
        continue;
      }
      DWORD mode = PIPE_READMODE_MESSAGE | PIPE_NOWAIT;
      if (!SetNamedPipeHandleState(pipe, &mode, nullptr, nullptr)) {
        core_.set_authorized(false);
        std::fill(key.begin(), key.end(), std::uint8_t{0});
        CloseHandle(pipe);
        pipe = INVALID_HANDLE_VALUE;
        continue;
      }
      // Copy audio only while a receiver owns this authenticated session.
      // Disconnecting the receiver returns the callback to its bounded fast path.
      core_.set_authorized(true);
    }

    if (!core_.try_pop(frame)) {
      std::this_thread::sleep_for(std::chrono::milliseconds(2));
      continue;
    }

    WireHeader header{};
    header.header_bytes = static_cast<std::uint16_t>(sizeof(header));
    header.sequence = sequence++;
    header.timestamp_ns = frame.timestamp_ns;
    header.frames = frame.frames;
    header.planes = frame.planes;
    header.sample_count = frame.sample_count;
    header.payload_bytes = frame.sample_count * static_cast<std::uint32_t>(sizeof(float));
    header.session_nonce = nonce_;

    if (!compute_hmac(key, header, frame, header.hmac_sha256) ||
        !write_exact(pipe, &header, static_cast<std::uint32_t>(sizeof(header))) ||
        !write_exact(pipe, frame.samples.data(), header.payload_bytes)) {
      transport_drops_.fetch_add(1, std::memory_order_relaxed);
      core_.set_authorized(false);
      std::fill(key.begin(), key.end(), std::uint8_t{0});
      CloseHandle(pipe);
      pipe = INVALID_HANDLE_VALUE;
      continue;
    }
    sent_frames_.fetch_add(1, std::memory_order_relaxed);
  }
  core_.set_authorized(false);
  if (pipe != INVALID_HANDLE_VALUE) CloseHandle(pipe);
  std::fill(key.begin(), key.end(), std::uint8_t{0});
  std::fill(nonce_.begin(), nonce_.end(), std::uint8_t{0});
#endif
  running_.store(false, std::memory_order_release);
}

}  // namespace bai::obs_capture
