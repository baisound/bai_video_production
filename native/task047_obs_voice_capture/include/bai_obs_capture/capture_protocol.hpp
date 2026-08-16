#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

namespace bai::obs_capture {

inline constexpr std::uint32_t kWireMagic = 0x31495642U;  // BVI1, little-endian
inline constexpr std::uint16_t kWireVersion = 1;
inline constexpr std::uint32_t kMaxFramesPerCallback = 8192;
inline constexpr std::uint32_t kMaxPlanes = 8;
inline constexpr std::size_t kQueueCapacity = 64;
inline constexpr std::size_t kSessionKeyBytes = 32;
inline constexpr std::size_t kNonceBytes = 16;
inline constexpr std::size_t kMacBytes = 32;
inline constexpr wchar_t kPipeName[] = L"\\\\.\\pipe\\bai-voice-capture-v1";
inline constexpr std::uint32_t kSessionHelloMagic = 0x32484342U;  // BCH2, little-endian
inline constexpr std::uint16_t kSessionHelloVersion = 2;

struct AudioFrame final {
  std::uint64_t timestamp_ns{0};
  std::uint32_t frames{0};
  std::uint32_t planes{0};
  std::uint32_t sample_count{0};
  std::array<float, static_cast<std::size_t>(kMaxFramesPerCallback) * kMaxPlanes> samples{};
};

#pragma pack(push, 1)
struct WireHeader final {
  std::uint32_t magic{kWireMagic};
  std::uint16_t version{kWireVersion};
  std::uint16_t header_bytes{0};
  std::uint64_t sequence{0};
  std::uint64_t timestamp_ns{0};
  std::uint32_t frames{0};
  std::uint32_t planes{0};
  std::uint32_t sample_count{0};
  std::uint32_t payload_bytes{0};
  std::array<std::uint8_t, kNonceBytes> session_nonce{};
  std::array<std::uint8_t, kMacBytes> hmac_sha256{};
};

struct SessionHello final {
  std::uint32_t magic{kSessionHelloMagic};
  std::uint16_t version{kSessionHelloVersion};
  std::uint16_t header_bytes{0};
  std::array<std::uint8_t, kSessionKeyBytes> session_key{};
};
#pragma pack(pop)

static_assert(sizeof(float) == 4, "The wire format requires IEEE-754 32-bit float storage");
static_assert(sizeof(SessionHello) == 40, "The controller handshake must remain fixed-width");

}  // namespace bai::obs_capture
