-- premake5.lua
--
-- Placeholder premake5 configuration. Replace targets/settings below with
-- your actual project. See docs/cpp/README.md for build instructions.
--
-- TODO: consider reading shared metadata (name/version) from ../project.ini
-- here so this file doesn't duplicate values maintained there.

workspace "YourProjectName"
    configurations { "Debug", "Release" }
    location "build"

project "your-lib"
    kind "StaticLib"
    language "C++"
    cppdialect "C++17"  -- keep in sync with project.ini [compatibility] cpp_standard
    targetdir "build/bin/%{cfg.buildcfg}"
    objdir "build/obj/%{cfg.buildcfg}"

    files { "src/**.h", "src/**.hpp", "src/**.cpp" }

    filter "configurations:Debug"
        defines { "DEBUG" }
        symbols "On"

    filter "configurations:Release"
        defines { "NDEBUG" }
        optimize "On"

project "your-tool"
    kind "ConsoleApp"
    language "C++"
    cppdialect "C++17"
    targetdir "build/bin/%{cfg.buildcfg}"
    objdir "build/obj/%{cfg.buildcfg}"

    files { "tool/**.h", "tool/**.hpp", "tool/**.cpp" }

    links { "your-lib" }
    includedirs { "src" }
