#include "bai_obs_capture/bounded_spsc_queue.hpp"

#include <cstdint>
#include <iostream>

bool run_queue_tests() {
  bai::obs_capture::BoundedSpscQueue<std::uint32_t, 4> queue;
  for (std::uint32_t value = 1; value <= 4; ++value) {
    if (!queue.try_write([&](std::uint32_t &slot) noexcept { slot = value; })) return false;
  }
  if (queue.try_write([](std::uint32_t &slot) noexcept { slot = 99; })) return false;
  if (queue.size_approx() != 4) return false;

  for (std::uint32_t expected = 1; expected <= 4; ++expected) {
    std::uint32_t actual = 0;
    if (!queue.try_pop(actual) || actual != expected) return false;
  }
  std::uint32_t empty = 0;
  if (queue.try_pop(empty) || queue.size_approx() != 0) return false;
  std::cout << "queue_tests=PASS\n";
  return true;
}
