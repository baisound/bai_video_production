#include "bai_obs_capture/capture_core.hpp"

#include <algorithm>

namespace bai::obs_capture {

namespace {
void update_max(std::atomic<std::uint32_t> &target, std::uint32_t value) noexcept {
  auto current = target.load(std::memory_order_relaxed);
  while (current < value &&
         !target.compare_exchange_weak(current, value, std::memory_order_relaxed)) {
  }
}
}  // namespace

void CaptureCore::set_authorized(bool authorized) noexcept {
  authorized_.store(authorized, std::memory_order_release);
}

bool CaptureCore::authorized() const noexcept {
  return authorized_.load(std::memory_order_acquire);
}

bool CaptureCore::on_audio(const std::array<const float *, kMaxPlanes> &planes,
                           std::uint32_t plane_count, std::uint32_t frames,
                           std::uint64_t timestamp_ns) noexcept {
  if (!authorized()) {
    dropped_unauthorized_.fetch_add(1, std::memory_order_relaxed);
    return false;
  }
  update_max(max_frames_observed_, frames);
  update_max(max_planes_observed_, plane_count);
  if (plane_count == 0 || frames == 0) {
    dropped_invalid_.fetch_add(1, std::memory_order_relaxed);
    return false;
  }
  if (plane_count > kMaxPlanes || frames > kMaxFramesPerCallback) {
    dropped_oversize_.fetch_add(1, std::memory_order_relaxed);
    return false;
  }
  for (std::uint32_t plane = 0; plane < plane_count; ++plane) {
    if (planes[plane] == nullptr) {
      dropped_invalid_.fetch_add(1, std::memory_order_relaxed);
      return false;
    }
  }

  const auto accepted = queue_.try_write([&](AudioFrame &out) noexcept {
    out.timestamp_ns = timestamp_ns;
    out.frames = frames;
    out.planes = plane_count;
    out.sample_count = frames * plane_count;
    std::size_t destination = 0;
    for (std::uint32_t plane = 0; plane < plane_count; ++plane) {
      const auto *source = planes[plane];
      std::copy_n(source, frames, out.samples.begin() + static_cast<std::ptrdiff_t>(destination));
      destination += frames;
    }
  });

  if (!accepted) {
    dropped_full_.fetch_add(1, std::memory_order_relaxed);
    return false;
  }
  accepted_.fetch_add(1, std::memory_order_relaxed);
  return true;
}

bool CaptureCore::try_pop(AudioFrame &frame) noexcept { return queue_.try_pop(frame); }

CaptureMetrics CaptureCore::metrics() const noexcept {
  return CaptureMetrics{accepted_.load(std::memory_order_relaxed),
                        dropped_full_.load(std::memory_order_relaxed),
                        dropped_oversize_.load(std::memory_order_relaxed),
                        dropped_invalid_.load(std::memory_order_relaxed),
                        dropped_unauthorized_.load(std::memory_order_relaxed),
                        max_frames_observed_.load(std::memory_order_relaxed),
                        max_planes_observed_.load(std::memory_order_relaxed)};
}

std::size_t CaptureCore::queued_approx() const noexcept { return queue_.size_approx(); }

}  // namespace bai::obs_capture
