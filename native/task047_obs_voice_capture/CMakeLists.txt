cmake_minimum_required(VERSION 3.28...3.30)

set(BAI_VOICE_CAPTURE_VERSION "0.1.0-dev.10")

add_library(bai-voice-capture MODULE)
add_library(BAI::voice-capture ALIAS bai-voice-capture)

target_sources(
  bai-voice-capture
  PRIVATE
    src/capture_core.cpp
    src/ipc_client.cpp
    src/obs_plugin.cpp
    include/bai_obs_capture/bounded_spsc_queue.hpp
    include/bai_obs_capture/capture_protocol.hpp
    include/bai_obs_capture/capture_core.hpp
    include/bai_obs_capture/ipc_client.hpp
)
target_include_directories(bai-voice-capture PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/include")
target_compile_features(bai-voice-capture PRIVATE cxx_std_17)
target_compile_definitions(
  bai-voice-capture PRIVATE
  BAI_VOICE_CAPTURE_VERSION="${BAI_VOICE_CAPTURE_VERSION}"
  WIN32_LEAN_AND_MEAN
  NOMINMAX
)
target_link_libraries(
  bai-voice-capture PRIVATE OBS::libobs
  $<$<PLATFORM_ID:Windows>:bcrypt>
  $<$<PLATFORM_ID:Windows>:advapi32>
)
set_target_properties_obs(bai-voice-capture PROPERTIES FOLDER plugins PREFIX "")

add_executable(bai-voice-capture-core-test)
target_sources(
  bai-voice-capture-core-test
  PRIVATE
    src/capture_core.cpp
    src/ipc_client.cpp
    tests/queue_tests.cpp
    tests/capture_core_tests.cpp
    tests/security_tests.cpp
)
target_include_directories(bai-voice-capture-core-test PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/include")
target_compile_features(bai-voice-capture-core-test PRIVATE cxx_std_17)
target_compile_definitions(bai-voice-capture-core-test PRIVATE WIN32_LEAN_AND_MEAN NOMINMAX)
target_link_libraries(
  bai-voice-capture-core-test PRIVATE
  $<$<PLATFORM_ID:Windows>:bcrypt>
  $<$<PLATFORM_ID:Windows>:advapi32>
)

if(MSVC)
  target_compile_options(bai-voice-capture PRIVATE /W4 /WX /permissive- /EHsc /wd4201 /wd4324)
  target_compile_options(bai-voice-capture-core-test PRIVATE /W4 /WX /permissive- /EHsc /wd4324)
endif()

enable_testing()
add_test(NAME bai-voice-capture-core-test COMMAND bai-voice-capture-core-test)

install(
  TARGETS bai-voice-capture
  RUNTIME DESTINATION "obs-plugins/64bit"
  LIBRARY DESTINATION "obs-plugins/64bit"
  COMPONENT bai-voice-capture
)
install(
  DIRECTORY resources/locale/
  DESTINATION "data/obs-plugins/bai-voice-capture/locale"
  COMPONENT bai-voice-capture
)
