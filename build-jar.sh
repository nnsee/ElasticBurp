#!/bin/bash
set -eE

JYTHON_URL="https://repo1.maven.org/maven2/org/python/jython-standalone/2.7.2/jython-standalone-2.7.2.jar"
PROJECT_NAME="ElasticBurp"

_JYTHON_JAR_PATH_NEEDS_DELETE=0
_SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

__check_for_binary() (
  type -p "$@" > /dev/null
)

pre_check() {
  declare -a missing=()
  __check_for_binary curl    || missing+=(curl)
  __check_for_binary javac   || missing+=(javac)
  __check_for_binary zip     || missing+=(zip)
  __check_for_binary python2 || missing+=(python2)
  if (( ${#missing[@]} > 0)); then
    echo "Missing required tools: ${missing[@]}"
    return 1
  fi

  return 0
}

cleanup() {
  _RETCODE=$?
  set +eE
  trap '' INT ERR EXIT
  if [ -n "$NO_BUILD_CLEANUP" ]; then
    echo "NO_BUILD_CLEANUP set, not cleaning up"
    exit
  fi

  echo "Cleaning up..."

  [ "$_JYTHON_JAR_PATH_NEEDS_DELETE" -eq 1 ] && rm "$JYTHON_JAR_PATH"
  [ -n "$_TMP_WORKDIR" ] && rm -rf "$_TMP_WORKDIR"
  exit "$_RETCODE"
}

download_jython() {
  JYTHON_JAR_PATH=$(mktemp --suffix .jar)
  echo "Downloading Jython to $JYTHON_JAR_PATH..."
  _JYTHON_JAR_PATH_NEEDS_DELETE=1
  curl -L "$JYTHON_URL" --output "$JYTHON_JAR_PATH"
}

set_up_dir() {
  _TMP_WORKDIR=$(mktemp -d)
  echo "Using temporary directory $_TMP_WORKDIR"
  mkdir "$_TMP_WORKDIR/Lib/"
  cp "$JYTHON_JAR_PATH" "$_TMP_WORKDIR/build.jar"
}

get_python_packages() {
  echo "Installing required packages using pip..."
  python2 -m pip install --target "$_TMP_WORKDIR/Lib/" -r "$_SCRIPT_DIR/requirements.txt"
}

copy_over_source() {
  echo "Copying over source files..."
  cp -r "$_SCRIPT_DIR/$PROJECT_NAME" "$_TMP_WORKDIR/Lib"
}

build_java_shim() {
  echo "Building jar shim files..."
  javac -cp "$_TMP_WORKDIR/build.jar" -d "$_TMP_WORKDIR" "$_SCRIPT_DIR/JarShim/burp/"*.java
}

bundle_jar() (
  echo "Bundling jar..."
  cd "$_TMP_WORKDIR"
  zip -qr build.jar Lib
  zip -qr build.jar burp
)

copy_artifact() {
  _OUT_DIR="$_SCRIPT_DIR/out"
  _OUT_FILENAME="$PROJECT_NAME-$(date '+%F-%H-%M-%S').jar"
  echo "Copying bundled jar to '$_OUT_DIR/$_OUT_FILENAME'..."
  mkdir -p "$_OUT_DIR" || true
  cp "$_TMP_WORKDIR/build.jar" "$_OUT_DIR/$_OUT_FILENAME"
}

symlink_latest() (
  # depends on copy_artifact being run
  _LATEST_PATH="latest.jar"
  cd "$_OUT_DIR"
  [ -L "$_LATEST_PATH" ] && rm "$_LATEST_PATH"
  if [ -e "$_LATEST_PATH" ]; then
    echo "Unable to create a symbolic link because '$_LATEST_PATH' exists and isn't a symlink!"
  else
    ln -s "$_OUT_FILENAME" "$_LATEST_PATH"
    echo "Created symbolic link: '$_OUT_FILENAME' -> '$_LATEST_PATH'"
  fi
)

main() {
  pre_check
  trap cleanup INT ERR EXIT
  [ -z "$JYTHON_JAR_PATH" ] && download_jython
  set_up_dir
  get_python_packages
  copy_over_source
  build_java_shim
  bundle_jar
  copy_artifact
  symlink_latest
}

main
