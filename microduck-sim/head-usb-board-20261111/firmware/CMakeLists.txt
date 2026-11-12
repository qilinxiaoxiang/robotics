cmake_minimum_required(VERSION 3.13)

# The Pico SDK is a fetched build dependency (tools/fetch_deps.sh puts it in .deps/); nothing of it is in this folder.
if (NOT DEFINED PICO_SDK_PATH)
    if (DEFINED ENV{PICO_SDK_PATH})
        set(PICO_SDK_PATH $ENV{PICO_SDK_PATH})
    else ()
        set(PICO_SDK_PATH ${CMAKE_CURRENT_LIST_DIR}/.deps/pico-sdk)
    endif ()
endif ()

set(PICO_BOARD_HEADER_DIRS ${CMAKE_CURRENT_LIST_DIR}/boards)
set(PICO_BOARD microduck_head_usb)

include(${PICO_SDK_PATH}/external/pico_sdk_import.cmake)

project(microduck_head_usb C CXX ASM)
set(CMAKE_C_STANDARD 11)

pico_sdk_init()

add_executable(head_usb
    src/main.c
    src/audio.c
    src/touch.c
    src/touch_format.c
    src/usb_audio.c
    src/usb_descriptors.c
)

pico_generate_pio_header(head_usb ${CMAKE_CURRENT_LIST_DIR}/src/i2s_mic.pio)
pico_generate_pio_header(head_usb ${CMAKE_CURRENT_LIST_DIR}/src/i2s_spk.pio)

target_include_directories(head_usb PRIVATE ${CMAKE_CURRENT_LIST_DIR}/src)

# Warnings for this project's own sources only (the SDK and TinyUSB are compiled with their own settings).
set_source_files_properties(
    src/main.c src/audio.c src/touch.c src/touch_format.c src/usb_audio.c src/usb_descriptors.c
    PROPERTIES COMPILE_OPTIONS "-Wall;-Wextra;-Wshadow;-Wconversion;-Wno-sign-conversion"
)

target_link_libraries(head_usb
    pico_stdlib
    pico_multicore
    pico_unique_id
    hardware_clocks
    hardware_dma
    hardware_i2c
    hardware_pio
    tinyusb_device
)

pico_enable_stdio_uart(head_usb 1)
pico_enable_stdio_usb(head_usb 0)

pico_set_program_name(head_usb "microduck_head_usb")
pico_set_program_version(head_usb "0.1.0")

pico_add_extra_outputs(head_usb)   # .uf2, .bin, .hex, .dis, .map
