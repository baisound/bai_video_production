#include "bai_obs_capture/capture_protocol.hpp"
#include "bai_obs_capture/ipc_client.hpp"

#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <iostream>
#include <memory>
#include <string>
#include <thread>
#include <vector>

#ifdef _WIN32
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <Windows.h>
#endif

namespace {
#ifdef _WIN32
using namespace bai::obs_capture;

bool wait_authorized(CaptureCore &core, bool expected) {
  const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(3);
  while (std::chrono::steady_clock::now() < deadline) {
    if (core.authorized() == expected) return true;
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
  }
  return false;
}

bool connect_server(HANDLE server) {
  if (ConnectNamedPipe(server, nullptr)) return true;
  return GetLastError() == ERROR_PIPE_CONNECTED;
}

bool write_hello(HANDLE server, const SessionKey &key) {
  SessionHello hello{};
  hello.header_bytes = static_cast<std::uint16_t>(sizeof(hello));
  hello.session_key = key;
  DWORD written = 0;
  return WriteFile(server, &hello, static_cast<DWORD>(sizeof(hello)), &written, nullptr) &&
         written == sizeof(hello);
}

bool read_exact(HANDLE server, void *buffer, DWORD bytes) {
  auto *cursor = static_cast<std::uint8_t *>(buffer);
  DWORD offset = 0;
  while (offset < bytes) {
    DWORD received = 0;
    if (!ReadFile(server, cursor + offset, bytes - offset, &received, nullptr) || received == 0)
      return false;
    offset += received;
  }
  return true;
}

bool read_frame(HANDLE server, WireHeader &header) {
  if (!read_exact(server, &header, static_cast<DWORD>(sizeof(header)))) return false;
  std::vector<std::uint8_t> payload(header.payload_bytes);
  return header.magic == kWireMagic && header.version == kWireVersion &&
         header.header_bytes == sizeof(header) && header.payload_bytes > 0 &&
         read_exact(server, payload.data(), header.payload_bytes);
}

bool run_same_user_handshake_and_resume_test() {
  const auto fail = [](const char *reason) {
    std::cerr << "same_user_handshake_failure=" << reason << " win32=" << GetLastError() << '\n';
    return false;
  };
  const std::wstring pipe_name = L"\\\\.\\pipe\\bai-voice-capture-test-" +
                                 std::to_wstring(GetCurrentProcessId()) + L"-" +
                                 std::to_wstring(GetTickCount64());
  auto core = std::make_unique<CaptureCore>();
  IpcClient client(*core, pipe_name.c_str());
  SessionKey key{};
  for (std::size_t i = 0; i < key.size(); ++i) key[i] = static_cast<std::uint8_t>(i + 1U);
  std::array<std::uint8_t, kNonceBytes> first_nonce{};
  std::uint64_t first_sequence = 0;

  if (!client.start()) return fail("client_start");
  for (std::uint64_t pass = 0; pass < 2; ++pass) {
    HANDLE server = CreateNamedPipeW(pipe_name.c_str(), PIPE_ACCESS_DUPLEX,
                                     PIPE_TYPE_MESSAGE | PIPE_READMODE_MESSAGE | PIPE_WAIT,
                                     1, 1048576, 4096, 0, nullptr);
    if (server == INVALID_HANDLE_VALUE) return fail("create_server");
    if (!connect_server(server) || !write_hello(server, key) || !wait_authorized(*core, true)) {
      CloseHandle(server);
      return fail("connect_hello_authorize");
    }
    std::array<float, 4> left{0.1F, 0.2F, 0.3F, 0.4F};
    std::array<float, 4> right{-0.1F, -0.2F, -0.3F, -0.4F};
    std::array<const float *, kMaxPlanes> planes{};
    planes[0] = left.data();
    planes[1] = right.data();
    if (!core->on_audio(planes, 2, 4, 500 + pass)) {
      CloseHandle(server);
      return fail("queue_frame");
    }
    WireHeader header{};
    if (!read_frame(server, header) || (pass == 0 && header.sequence != 0) ||
        (pass == 1 && header.sequence <= first_sequence)) {
      CloseHandle(server);
      return fail("read_frame_or_sequence");
    }
    if (pass == 0) {
      first_nonce = header.session_nonce;
      first_sequence = header.sequence;
    }
    else if (header.session_nonce != first_nonce) {
      CloseHandle(server);
      return fail("nonce_changed");
    }
    DisconnectNamedPipe(server);
    CloseHandle(server);
    core->on_audio(planes, 2, 4, 700 + pass);
    if (!wait_authorized(*core, false)) return fail("disconnect_not_observed");
  }
  client.stop();
  if (client.running() || core->authorized()) return fail("client_stop_state");
  if (client.handshake_failures() != 0) return fail("unexpected_handshake_failure");
  return true;
}
#endif
}  // namespace

bool run_security_tests() {
  using namespace bai::obs_capture;
  auto core = std::make_unique<CaptureCore>();
  IpcClient client(*core);
  if (!client.start()) { std::cerr << "security_failure=basic_start\n"; return false; }
  if (!client.running()) { std::cerr << "security_failure=basic_running\n"; return false; }
  std::this_thread::sleep_for(std::chrono::milliseconds(20));
  client.stop();
  if (client.running()) { std::cerr << "security_failure=basic_stop\n"; return false; }
  if (core->authorized()) { std::cerr << "security_failure=basic_authorized\n"; return false; }
  if (sizeof(WireHeader) != 88) return false;
  if (sizeof(SessionHello) != 40 || kSessionHelloVersion != 2) return false;
  if (kPipeName[0] != L'\\' || kQueueCapacity != 64 || kMaxFramesPerCallback != 8192) return false;
#ifdef _WIN32
  if (!run_same_user_handshake_and_resume_test()) return false;
#endif
  std::cout << "security_tests=PASS\n";
  return true;
}
