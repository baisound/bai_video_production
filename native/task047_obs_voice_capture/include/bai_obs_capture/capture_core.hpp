#pragma once

#include "bai_obs_capture/bounded_spsc_queue.hpp"
#include "bai_obs_capture/capture_protocol.hpp"

#include <array>
#include <atomic>
#include <cstdint>

namespace bai::obs_capture {

struct CaptureMetrics final {
  std::uint64_t accepted{0};
  std::uint64_t dropped_full{0};
  std::uint64_t dropped_oversize{0};
  std::uint64_t dropped_invalid{0};
  std::uint64_t dropped_unauthorized{0};
  std::uint32_t max_frames_observed{0};
  std::uint32_t max_planes_observed{0};
};

class CaptureCore final {
 public:
  CaptureCore() = default;
  CaptureCore(const CaptureCore &) = delete;
  CaptureCore &operator=(const CaptureCore &) = delete;

  void set_authorized(bool authorized) noexcept;
  [[nodiscard]] bool authorized() const noexcept;

  bool on_audio(const std::array<const float *, kMaxPlanes> &planes,
                std::uint32_t plane_count, std::uint32_t frames,
                std::uint64_t timestamp_ns) noexcept;

  bool try_pop(AudioFrame &frame) noexcept;
  [[nodiscard]] CaptureMetrics metrics() const noexcept;
  [[nodiscard]] std::size_t queued_approx() const noexcept;

 private:
  BoundedSpscQueue<AudioFrame, kQueueCapacity> queue_{};
  std::atomic<bool> authorized_{false};
  std::atomic<std::uint64_t> accepted_{0};
  std::atomic<std::uint64_t> dropped_full_{0};
  std::atomic<std::uint64_t> dropped_oversize_{0};
  std::atomic<std::uint64_t> dropped_invalid_{0};
  std::atomic<std::uint64_t> dropped_unauthorized_{0};
  std::atomic<std::uint32_t> max_frames_observed_{0};
  std::atomic<std::uint32_t> max_planes_observed_{0};
};

}  // namespace bai::obs_capture
