#pragma once

#include <array>
#include <atomic>
#include <cstddef>
#include <utility>

namespace bai::obs_capture {

template <typename T, std::size_t Capacity>
class BoundedSpscQueue final {
  static_assert(Capacity > 0, "Capacity must be positive");

 public:
  BoundedSpscQueue() = default;
  BoundedSpscQueue(const BoundedSpscQueue &) = delete;
  BoundedSpscQueue &operator=(const BoundedSpscQueue &) = delete;

  template <typename Writer>
  bool try_write(Writer &&writer) noexcept(noexcept(writer(std::declval<T &>()))) {
    const auto head = head_.load(std::memory_order_relaxed);
    const auto next = increment(head);
    if (next == tail_.load(std::memory_order_acquire)) {
      return false;
    }
    writer(storage_[head]);
    head_.store(next, std::memory_order_release);
    return true;
  }

  bool try_pop(T &out) noexcept(noexcept(out = std::declval<const T &>())) {
    const auto tail = tail_.load(std::memory_order_relaxed);
    if (tail == head_.load(std::memory_order_acquire)) {
      return false;
    }
    out = storage_[tail];
    tail_.store(increment(tail), std::memory_order_release);
    return true;
  }

  [[nodiscard]] std::size_t capacity() const noexcept { return Capacity; }

  [[nodiscard]] std::size_t size_approx() const noexcept {
    const auto head = head_.load(std::memory_order_acquire);
    const auto tail = tail_.load(std::memory_order_acquire);
    return head >= tail ? head - tail : storage_.size() - (tail - head);
  }

 private:
  static constexpr std::size_t increment(std::size_t value) noexcept {
    return (value + 1U) % (Capacity + 1U);
  }

  alignas(64) std::array<T, Capacity + 1U> storage_{};
  alignas(64) std::atomic<std::size_t> head_{0};
  alignas(64) std::atomic<std::size_t> tail_{0};
};

}  // namespace bai::obs_capture
