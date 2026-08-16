#pragma once

// Compile-only shape guard. This file is never used for a runtime package.
// Real plugin builds must include the verified OBS 32.2.1 headers first.

#include <cstdint>

#define MAX_AV_PLANES 8
#define OBS_DECLARE_MODULE()
#define OBS_MODULE_USE_DEFAULT_LOCALE(module, locale)
#define OBS_SOURCE_AUDIO 1U

struct obs_data;
struct obs_source;
struct obs_properties;
using obs_data_t = obs_data;
using obs_source_t = obs_source;
using obs_properties_t = obs_properties;

enum obs_source_type { OBS_SOURCE_TYPE_FILTER };
struct obs_audio_data {
  std::uint8_t *data[MAX_AV_PLANES];
  std::uint32_t frames;
  std::uint64_t timestamp;
};
struct obs_source_info {
  const char *id;
  obs_source_type type;
  std::uint32_t output_flags;
  const char *(*get_name)(void *);
  void *(*create)(obs_data_t *, obs_source_t *);
  void (*destroy)(void *);
  void (*update)(void *, obs_data_t *);
  void (*get_defaults)(obs_data_t *);
  obs_properties_t *(*get_properties)(void *);
  obs_audio_data *(*filter_audio)(void *, obs_audio_data *);
};

const char *obs_module_text(const char *);
bool obs_data_get_bool(obs_data_t *, const char *);
void obs_data_set_default_bool(obs_data_t *, const char *, bool);
obs_properties_t *obs_properties_create();
void obs_properties_add_bool(obs_properties_t *, const char *, const char *);
void obs_register_source(obs_source_info *);
