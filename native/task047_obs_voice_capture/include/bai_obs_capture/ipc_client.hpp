#pragma once

#include "bai_obs_capture/capture_core.hpp"

#include <array>
#include <atomic>
#include <cstdint>
#include <string>
#include <thread>

namespace bai::obs_capture {

using SessionKey = std::array<std::uint8_t, kSessionKeyBytes>;

class IpcClient final {
 public:
  explicit IpcClient(CaptureCore &core, const wchar_t *pipe_name = kPipeName);
  ~IpcClient();
  IpcClient(const IpcClient &) = delete;
  IpcClient &operator=(const IpcClient &) = delete;

  bool start();
  void stop() noexcept;
  [[nodiscard]] bool running() const noexcept;
  [[nodiscard]] std::uint64_t sent_frames() const noexcept;
  [[nodiscard]] std::uint64_t transport_drops() const noexcept;
  [[nodiscard]] std::uint64_t handshake_failures() const noexcept;

 private:
  void worker_main() noexcept;

  CaptureCore &core_;
  std::wstring pipe_name_;
  std::array<std::uint8_t, kNonceBytes> nonce_{};
  std::atomic<bool> running_{false};
  std::atomic<bool> stop_requested_{false};
  std::atomic<std::uint64_t> sent_frames_{0};
  std::atomic<std::uint64_t> transport_drops_{0};
  std::atomic<std::uint64_t> handshake_failures_{0};
  std::thread worker_{};
};

}  // namespace bai::obs_capture
