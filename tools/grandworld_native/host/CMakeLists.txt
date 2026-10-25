cmake_minimum_required(VERSION 3.16)
project(grandworld_native_host_probe C)

set(CMAKE_C_STANDARD 99)
find_package(SDL2 CONFIG QUIET)
if(SDL2_FOUND AND TARGET SDL2::SDL2)
    set(GW_SDL SDL2::SDL2)
else()
    find_package(PkgConfig REQUIRED)
    pkg_check_modules(SDL2 REQUIRED IMPORTED_TARGET sdl2)
    set(GW_SDL PkgConfig::SDL2)
endif()

find_package(SDL2_image CONFIG QUIET)
if(SDL2_image_FOUND AND TARGET SDL2_image::SDL2_image)
    set(GW_SDL_IMAGE SDL2_image::SDL2_image)
else()
    find_package(PkgConfig REQUIRED)
    pkg_check_modules(SDL2_IMAGE REQUIRED IMPORTED_TARGET SDL2_image)
    set(GW_SDL_IMAGE PkgConfig::SDL2_IMAGE)
endif()

add_library(gw_native_host STATIC gw_sdl_host.c gw_style_index.c gw_follower_visual.c)
target_include_directories(gw_native_host PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(gw_native_host PUBLIC ${GW_SDL} ${GW_SDL_IMAGE})

add_executable(gw_host_smoke gw_host_smoke.c)
target_link_libraries(gw_host_smoke PRIVATE gw_native_host)
enable_testing()
add_test(NAME host_frame_smoke COMMAND gw_host_smoke)
set_tests_properties(host_frame_smoke PROPERTIES ENVIRONMENT "SDL_VIDEODRIVER=dummy")

add_executable(gw_host_preview gw_host_preview.c)
target_link_libraries(gw_host_preview PRIVATE gw_native_host)
 
add_executable(gw_theme_lab gw_theme_lab.c)
target_link_libraries(gw_theme_lab PRIVATE gw_native_host)

add_executable(gw_style_smoke gw_style_smoke.c)
target_link_libraries(gw_style_smoke PRIVATE gw_native_host)

add_executable(gw_follower_visual_smoke gw_follower_visual_smoke.c gw_follower_visual.c)
add_test(NAME follower_eight_look_four_grid COMMAND gw_follower_visual_smoke)
