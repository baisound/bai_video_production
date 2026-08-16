#include "bai_obs_capture/capture_core.hpp"
#include "bai_obs_capture/ipc_client.hpp"

#include <obs-module.h>

#include <array>
#include <memory>

OBS_DECLARE_MODULE()
OBS_MODULE_USE_DEFAULT_LOCALE("bai-voice-capture", "en-US")

namespace {
using bai::obs_capture::CaptureCore;
using bai::obs_capture::IpcClient;
using bai::obs_capture::kMaxPlanes;

constexpr const char *kFilterId = "bai_voice_capture_filter";
constexpr const char *kEnabledSetting = "capture_enabled";
constexpr const char *kStatusProperty = "capture_status";
constexpr const char *kDestinationProperty = "capture_destination";

struct FilterContext final {
  obs_source_t *source{nullptr};
  CaptureCore core{};
  std::unique_ptr<IpcClient> ipc{};
};

void log_summary(const FilterContext &context, const char *reason) {
  const auto metrics = context.core.metrics();
  const auto sent = context.ipc ? context.ipc->sent_frames() : 0U;
  const auto transport_drops = context.ipc ? context.ipc->transport_drops() : 0U;
  const auto handshake_failures = context.ipc ? context.ipc->handshake_failures() : 0U;
  blog(LOG_INFO,
       "[bai-voice-capture] %s accepted=%llu sent=%llu queue_full=%llu oversize=%llu "
       "invalid=%llu unauthorized=%llu transport_drops=%llu handshake_failures=%llu "
       "max_frames=%u max_planes=%u",
       reason, static_cast<unsigned long long>(metrics.accepted),
       static_cast<unsigned long long>(sent),
       static_cast<unsigned long long>(metrics.dropped_full),
       static_cast<unsigned long long>(metrics.dropped_oversize),
       static_cast<unsigned long long>(metrics.dropped_invalid),
       static_cast<unsigned long long>(metrics.dropped_unauthorized),
       static_cast<unsigned long long>(transport_drops),
       static_cast<unsigned long long>(handshake_failures), metrics.max_frames_observed,
       metrics.max_planes_observed);
}

const char *filter_name(void *) { return obs_module_text("Filter.Name"); }

void apply_settings(FilterContext &context, obs_data_t *settings) {
  const bool enabled = obs_data_get_bool(settings, kEnabledSetting);
  if (!enabled) {
    log_summary(context, "capture disabled");
    context.core.set_authorized(false);
    if (context.ipc) context.ipc->stop();
    context.ipc.reset();
    return;
  }

  if (!context.ipc) {
    context.core.set_authorized(false);
    context.ipc = std::make_unique<IpcClient>(context.core);
    if (!context.ipc->start()) {
      blog(LOG_WARNING, "[bai-voice-capture] capture denied: IPC worker did not start");
      context.ipc.reset();
      context.core.set_authorized(false);
      return;
    }
  }
  obs_source_set_name(context.source, obs_module_text("Filter.ControllerManagedName"));
  blog(LOG_INFO,
       "[bai-voice-capture] control worker armed; waiting for same-user controller handshake");
}

void *filter_create(obs_data_t *settings, obs_source_t *source) {
  auto context = std::make_unique<FilterContext>();
  context->source = source;
  apply_settings(*context, settings);
  return context.release();
}

void filter_destroy(void *data) {
  auto *context = static_cast<FilterContext *>(data);
  if (context == nullptr) return;
  log_summary(*context, "filter destroyed");
  context->core.set_authorized(false);
  if (context->ipc) context->ipc->stop();
  delete context;
}

void filter_update(void *data, obs_data_t *settings) {
  auto *context = static_cast<FilterContext *>(data);
  if (context != nullptr) apply_settings(*context, settings);
}

void filter_defaults(obs_data_t *settings) { obs_data_set_default_bool(settings, kEnabledSetting, false); }

obs_properties_t *filter_properties(void *data) {
  auto *context = static_cast<FilterContext *>(data);
  obs_properties_t *properties = obs_properties_create();
  obs_properties_add_bool(properties, kEnabledSetting, obs_module_text("Capture.Enabled"));
  const bool active = context != nullptr && context->core.authorized() && context->ipc && context->ipc->running();
  obs_properties_add_text(properties, kStatusProperty,
                          obs_module_text(active ? "Capture.StatusActive" : "Capture.StatusStopped"),
                          OBS_TEXT_INFO);
  obs_properties_add_text(properties, kDestinationProperty,
                          obs_module_text("Capture.DestinationManagedExternally"), OBS_TEXT_INFO);
  return properties;
}

obs_audio_data *filter_audio(void *data, obs_audio_data *audio) {
  auto *context = static_cast<FilterContext *>(data);
  if (context == nullptr || audio == nullptr) return audio;

  std::array<const float *, kMaxPlanes> planes{};
  std::uint32_t plane_count = 0;
  for (std::uint32_t index = 0; index < kMaxPlanes; ++index) {
    if (audio->data[index] == nullptr) break;
    planes[index] = reinterpret_cast<const float *>(audio->data[index]);
    ++plane_count;
  }
  context->core.on_audio(planes, plane_count, audio->frames, audio->timestamp);
  return audio;
}

obs_source_info filter_info = [] {
  obs_source_info info{};
  info.id = kFilterId;
  info.type = OBS_SOURCE_TYPE_FILTER;
  info.output_flags = OBS_SOURCE_AUDIO;
  info.get_name = filter_name;
  info.create = filter_create;
  info.destroy = filter_destroy;
  info.update = filter_update;
  info.get_defaults = filter_defaults;
  info.get_properties = filter_properties;
  info.filter_audio = filter_audio;
  return info;
}();
}  // namespace

bool obs_module_load(void) {
  obs_register_source(&filter_info);
  return true;
}

const char *obs_module_description(void) {
  return "Bounded selected-source audio capture filter for authenticated local IPC";
}
