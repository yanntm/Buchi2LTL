#!/usr/bin/env bash
# install_gap.sh — Install GAP + SgpDec for the Krohn-Rhodes construction path.
#
# Supports: Fedora (dnf), Debian/Ubuntu (apt), and generic "build from source" fallback.
# Prefers a user-local installation under ~/.gap (no root required for the SgpDec part).
# After success, `gap --no-window -c 'LoadPackage("SgpDec"); Print("SgpDec OK\n");'` should work.
#
# Usage:
#   ./install_gap.sh
#   ./install_gap.sh --check-only
#
set -euo pipefail

GAP_MIN_VERSION="4.12"
SGPDEC_VERSION="v1.2.0"   # Update when a new release appears
SGPDEC_TARBALL="sgpdec-1.2.0.tar.gz"
SGPDEC_URL="https://github.com/gap-packages/sgpdec/releases/download/${SGPDEC_VERSION}/${SGPDEC_TARBALL}"

USER_GAP_DIR="${HOME}/.gap"
USER_PKG_DIR="${USER_GAP_DIR}/pkg"
GAP_CMD="${GAP_CMD:-gap}"

log() { echo "[bls/install] $*"; }
warn() { echo "[bls/install] WARNING: $*" >&2; }
die() { echo "[bls/install] ERROR: $*" >&2; exit 1; }

check_only=false
if [[ "${1:-}" == "--check-only" ]]; then
  check_only=true
fi

have_cmd() { command -v "$1" >/dev/null 2>&1; }

detect_distro() {
  if [[ -f /etc/fedora-release ]] || have_cmd dnf; then
    echo "fedora"
  elif [[ -f /etc/debian_version ]] || have_cmd apt-get; then
    echo "debian"
  else
    echo "unknown"
  fi
}

ensure_gap_base() {
  if have_cmd "$GAP_CMD"; then
    local ver
    ver=$($GAP_CMD --no-window --bare -c 'Print(GAPInfo.Version, "\n");' 2>/dev/null | tail -1 | tr -d '\r' || true)
    log "Found GAP: $ver (command: $GAP_CMD)"
    return 0
  fi

  local distro
  distro=$(detect_distro)
  log "GAP not found in PATH. distro=$distro"

  if $check_only; then
    die "GAP not found (check-only mode)."
  fi

  case "$distro" in
    fedora)
      log "Attempting dnf install (you may be prompted for sudo password)..."
      sudo dnf install -y gap gap-core gap-pkg-semigroups gap-pkg-digraphs gap-pkg-io gap-pkg-json || {
        warn "dnf install of some gap-pkg-* may have failed or been partial."
      }
      ;;
    debian)
      log "Attempting apt install (sudo may be required)..."
      sudo apt-get update -qq || true
      sudo apt-get install -y gap gap-core gap-dev gap-doc gap-online-help \
        gap-pkg-semigroups gap-pkg-digraphs gap-pkg-io || {
        warn "apt may not have all the -pkg packages under those exact names; check 'apt search gap'."
      }
      ;;
    *)
      warn "Unknown distro. Please install GAP 4.12+ manually (see https://www.gap-system.org/Install/)."
      die "Then re-run this script."
      ;;
  esac

  if ! have_cmd "$GAP_CMD"; then
    die "GAP still not found after attempted install. Check PATH or install manually."
  fi
  log "GAP now available."
}

install_sgpdec_user() {
  mkdir -p "$USER_PKG_DIR"
  local target_dir="${USER_PKG_DIR}/sgpdec"

  if [[ -d "$target_dir" ]]; then
    log "SgpDec directory already exists at $target_dir — skipping download."
    return 0
  fi

  if $check_only; then
    die "SgpDec not installed in user pkg dir (check-only)."
  fi

  log "Downloading SgpDec ${SGPDEC_VERSION} to user package dir..."
  local tmp
  tmp=$(mktemp -d)
  # Simple cleanup; avoid complex traps that can cause "unbound variable" noise on error paths.
  cleanup() { rm -rf "$tmp" 2>/dev/null || true; }
  trap cleanup EXIT

  curl -fL --progress-bar -o "$tmp/${SGPDEC_TARBALL}" "$SGPDEC_URL" || {
    # Fallback: try to clone the repo if release tarball layout changes
    warn "Direct release tarball download failed; trying git clone of tag..."
    git clone --depth 1 --branch "$SGPDEC_VERSION" https://github.com/gap-packages/sgpdec.git "$tmp/sgpdec-src" || \
      die "Could not obtain SgpDec sources."
    (cd "$tmp/sgpdec-src" && tar czf "$tmp/${SGPDEC_TARBALL}" .)
  }

  tar -xzf "$tmp/${SGPDEC_TARBALL}" -C "$tmp"
  # The tarball usually unpacks to a directory named sgpdec-1.2.0 or just "sgpdec"
  local unpacked
  unpacked=$(find "$tmp" -maxdepth 1 -type d -name "sgpdec*" | head -1)
  if [[ -z "$unpacked" ]]; then
    # Sometimes the tarball root is the package contents directly
    mkdir -p "$tmp/sgpdec-fallback"
    tar -xzf "$tmp/${SGPDEC_TARBALL}" -C "$tmp/sgpdec-fallback"
    unpacked="$tmp/sgpdec-fallback"
  fi

  cp -r "$unpacked" "$target_dir"
  log "Installed SgpDec to $target_dir"
}

verify_sgpdec() {
  log "Verifying SgpDec can be loaded..."
  # Keep verification minimal and robust: we only care that LoadPackage succeeds.
  # Do not rely on specific globals like SgpDecVersion (they may not be bound at top level in all versions).
  if $GAP_CMD --no-window --bare -c '
    if LoadPackage("SgpDec") = fail then
      Print("LOAD_FAIL\n");
    else
      Print("LOAD_OK\n");
    fi;
    QUIT;
  ' 2>&1 | tee /tmp/kr_gap_verify.log | grep -q "LOAD_OK"; then
    log "SUCCESS: SgpDec loads correctly."
    return 0
  else
    cat /tmp/kr_gap_verify.log || true
    die "SgpDec failed to load. See log above. Check that ~/.gap/pkg/sgpdec (or a system pkg dir) is visible to GAP."
  fi
}

main() {
  log "Starting GAP + SgpDec setup for BuchiToLTL/bls (Linux assumed)."
  ensure_gap_base
  install_sgpdec_user
  verify_sgpdec

  log "All done."
  log "You can now run Python code that calls into bls/gap/ (decompose_aut)."
  log "Example verification command:"
  echo "    $GAP_CMD --no-window -c 'LoadPackage(\"SgpDec\"); Print(\"HolonomyCascadeSemigroup example:\\n\"); T:=Semigroup([Transformation([2,1,3])]); HT:=HolonomyCascadeSemigroup(T); Print(HT, \"\\n\"); QUIT;'"
}

main "$@"
