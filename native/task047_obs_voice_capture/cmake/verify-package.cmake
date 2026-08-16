include_guard(GLOBAL)

if(NOT DEFINED BAI_VOICE_CAPTURE_PLUGIN_DIR)
  message(FATAL_ERROR "BAI_VOICE_CAPTURE_PLUGIN_DIR is required")
endif()

cmake_path(ABSOLUTE_PATH BAI_VOICE_CAPTURE_PLUGIN_DIR NORMALIZE OUTPUT_VARIABLE _bai_plugin_dir)
cmake_path(ABSOLUTE_PATH CMAKE_SOURCE_DIR NORMALIZE OUTPUT_VARIABLE _bai_obs_source_dir)
set(_bai_expected_dir "${_bai_obs_source_dir}/plugins/bai-voice-capture")
cmake_path(NORMAL_PATH _bai_expected_dir OUTPUT_VARIABLE _bai_expected_dir)

if(NOT _bai_plugin_dir STREQUAL _bai_expected_dir)
  message(FATAL_ERROR "TASK-047 plugin path escapes the verified OBS source tree")
endif()
if(NOT EXISTS "${_bai_plugin_dir}/CMakeLists.txt")
  message(FATAL_ERROR "TASK-047 plugin CMakeLists.txt is absent")
endif()

get_property(_bai_validated GLOBAL PROPERTY BAI_VOICE_CAPTURE_VALIDATED)
if(_bai_validated)
  message(FATAL_ERROR "TASK-047 duplicate plugin validation")
endif()
set_property(GLOBAL PROPERTY BAI_VOICE_CAPTURE_VALIDATED TRUE)

set(
  BAI_VOICE_CAPTURE_REGISTRATION_STATE
  "VALIDATED_PENDING_REGISTRATION"
  CACHE INTERNAL "TASK-047 registration state"
)
