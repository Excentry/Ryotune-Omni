set -euo pipefail

input="$(realpath "$1")"
output="$(realpath -m "$2")"
mkdir -p "$output"
exec > >(tee "$output/build.log") 2>&1
python3 "$input/recipe/prepare.py" --offline --cache "$input/archives" --output "$output/prepared"
sources="$output/prepared/sources"
prefix="$output/prefix"
builds="$output/builds"
mkdir -p "$prefix/lib/pkgconfig" "$builds" "$output/candidate"
unset CPATH C_INCLUDE_PATH CPLUS_INCLUDE_PATH LIBRARY_PATH CMAKE_PREFIX_PATH CMAKE_TOOLCHAIN_FILE PKG_CONFIG_SYSROOT_DIR
export CC=x86_64-w64-mingw32-gcc
export CXX=x86_64-w64-mingw32-g++
export AR=x86_64-w64-mingw32-ar
export RANLIB=x86_64-w64-mingw32-ranlib
export STRIP=x86_64-w64-mingw32-strip
export CC_FOR_BUILD=gcc
export CXX_FOR_BUILD=g++
export CFLAGS="-O2 -pipe -fstack-protector-strong"
export CXXFLAGS="$CFLAGS"
export CPPFLAGS=""
export LDFLAGS="-static-libgcc -static-libstdc++"
export PKG_CONFIG=pkg-config
export PKG_CONFIG_PATH=""
export PKG_CONFIG_LIBDIR="$prefix/lib/pkgconfig:$prefix/share/pkgconfig"
export SOURCE_DATE_EPOCH=1792591200
export PYTHONNOUSERSITE=1
unset PYTHONPATH
test "$($CC -dumpmachine)" = x86_64-w64-mingw32
{
    "$CC" --version
    "$CXX" --version
    meson --version
    ninja --version
    python3 --version
    pkg-config --version
} > "$output/toolchain.txt"
cat > "$output/cross.ini" <<EOF
[binaries]
c = '$CC'
cpp = '$CXX'
ar = '$AR'
strip = '$STRIP'
windres = 'x86_64-w64-mingw32-windres'
pkg-config = 'pkg-config'
[host_machine]
system = 'windows'
cpu_family = 'x86_64'
cpu = 'x86_64'
endian = 'little'
[properties]
needs_exe_wrapper = true
pkg_config_libdir = ['$prefix/lib/pkgconfig', '$prefix/share/pkgconfig']
EOF

meson_build() {
    local component="$1"
    shift
    meson setup "$builds/$component" "$sources/$component" \
        --cross-file "$output/cross.ini" --prefix "$prefix" --libdir lib \
        --buildtype release --default-library static --wrap-mode nofallback \
        -Dauto_features=disabled "$@"
    meson compile -C "$builds/$component" -j "${BUILD_JOBS:-2}"
    meson install -C "$builds/$component" --no-rebuild
    meson introspect "$builds/$component" --dependencies > "$output/$component-dependencies.json"
    meson introspect "$builds/$component" --buildoptions > "$output/$component-options.json"
}

meson_build freetype -Dharfbuzz=disabled -Dzlib=disabled
meson_build fribidi -Ddocs=false -Dbin=false -Dtests=false
meson_build harfbuzz -Dtests=disabled -Dutilities=disabled -Draster=disabled -Dvector=disabled -Dgpu=disabled -Dsubset=disabled
meson_build libass -Ddirectwrite=enabled
meson_build libplacebo -Ddemos=false -Dtests=false
meson_build rubberband -Dfft=builtin -Dresampler=builtin
meson_build libxml2 -Dthreads=enabled -Dwinpath=enabled

mkdir -p "$builds/ffmpeg"
(
    cd "$builds/ffmpeg"
    "$sources/ffmpeg/configure" --prefix="$prefix" --target-os=mingw32 --arch=x86_64 \
        --enable-cross-compile --cross-prefix=x86_64-w64-mingw32- \
        --pkg-config=pkg-config --pkg-config-flags=--static \
        --disable-autodetect --disable-programs --disable-doc --disable-debug \
        --enable-static --disable-shared --enable-gpl --enable-version3 \
        --enable-network --enable-schannel --enable-libxml2 --disable-iconv \
        --extra-cflags="$CFLAGS" --extra-cxxflags="$CXXFLAGS" --extra-ldflags="$LDFLAGS"
    make -j "${BUILD_JOBS:-2}"
    make install
)
meson_build mpv -Ddefault_library=shared -Dlibmpv=true -Dcplayer=false \
    -Dgpl=true -Dbuild-date=false -Dlua=disabled -Dgl=disabled \
    -Dwin32-threads=enabled -Dwasapi=enabled -Drubberband=enabled
grep -Eq '^#define HAVE_WASAPI 1$' "$builds/mpv/config.h"
grep -Eq '^#define HAVE_RUBBERBAND 1$' "$builds/mpv/config.h"
grep -Eq '^#define CONFIG_SCHANNEL 1$' "$builds/ffmpeg/config.h"
grep -Eq '^#define CONFIG_DASH_DEMUXER 1$' "$builds/ffmpeg/config_components.h"
for filter in VOLUME AECHO BASS STEREOWIDEN; do
    grep -Eq "^#define CONFIG_${filter}_FILTER 1$" "$builds/ffmpeg/config_components.h"
done
cp "$builds/mpv/libmpv-2.dll" "$output/candidate/"
cp "$builds/mpv/libmpv.dll.a" "$output/candidate/mpv.lib"
mkdir -p "$output/candidate/include/mpv"
cp "$sources/mpv/include/mpv/"*.h "$output/candidate/include/mpv/"
cp "$output/prepared/source-inputs.tar.gz" "$output/candidate/"
cp "$input/recipe/NOTICE.md" "$output/candidate/NOTICE.md"
cp "$output/toolchain.txt" "$output/candidate/"
x86_64-w64-mingw32-objdump -p "$output/candidate/libmpv-2.dll" > "$output/candidate/pe-imports.txt"
python3 "$input/recipe/package.py" "$output"
