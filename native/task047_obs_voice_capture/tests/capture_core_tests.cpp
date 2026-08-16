#include "bai_obs_capture/capture_core.hpp"

#include <array>
#include <cstdint>
#include <iostream>
#include <memory>

bool run_queue_tests();
bool run_security_tests();

namespace {
bool run_capture_tests() {
  using namespace bai::obs_capture;
  auto core = std::make_unique<CaptureCore>();
  std::array<float, 4> left{0.1F, 0.2F, 0.3F, 0.4F};
  std::array<float, 4> right{-0.1F, -0.2F, -0.3F, -0.4F};
  std::array<const float *, kMaxPlanes> planes{};
  planes[0] = left.data();
  planes[1] = right.data();

  if (core->on_audio(planes, 2, 4, 100)) return false;
  if (core->metrics().dropped_unauthorized != 1) return false;

  core->set_authorized(true);
  if (!core->on_audio(planes, 2, 4, 101)) return false;
  AudioFrame frame{};
  if (!core->try_pop(frame)) return false;
  if (frame.timestamp_ns != 101 || frame.frames != 4 || frame.planes != 2 || frame.sample_count != 8)
    return false;
  if (frame.samples[0] != left[0] || frame.samples[4] != right[0]) return false;

  if (core->on_audio(planes, 0, 4, 102)) return false;
  if (core->on_audio(planes, 2, kMaxFramesPerCallback + 1U, 103)) return false;
  auto invalid_planes = planes;
  invalid_planes[1] = nullptr;
  if (core->on_audio(invalid_planes, 2, 4, 104)) return false;

  for (std::size_t i = 0; i < kQueueCapacity; ++i) {
    if (!core->on_audio(planes, 2, 4, 200 + i)) return false;
  }
  if (core->on_audio(planes, 2, 4, 999)) return false;

  const auto metrics = core->metrics();
  if (metrics.accepted != kQueueCapacity + 1U || metrics.dropped_full != 1 ||
      metrics.dropped_oversize != 1 || metrics.dropped_invalid != 2 ||
      metrics.dropped_unauthorized != 1 ||
      metrics.max_frames_observed != kMaxFramesPerCallback + 1U ||
      metrics.max_planes_observed != 2U)
    return false;
  std::cout << "capture_core_tests=PASS\n";
  return true;
}
}  // namespace

int main() {
  if (!run_queue_tests()) return 1;
  if (!run_capture_tests()) return 2;
  if (!run_security_tests()) return 3;
  std::cout << "bai-voice-capture-core-test=PASS\n";
  return 0;
}
