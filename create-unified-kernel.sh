#!/bin/sh

# kernel variant: -zen, -hardened, etc
VARIANT=""

# file paths
LINUX="/boot/vmlinuz-linux${VARIANT}"
CMDLINE="/etc/cmdline"
INITRD="/boot/initramfs-linux${VARIANT}.img"
EFI="/efi/EFI/Linux/linux.efi"
SB_KEY="/etc/secureboot/keys/db/db.key"
SB_CERT="/etc/secureboot/keys/db/db.crt"
PCR_PRIVATE="/etc/systemd/tpm2-pcr-private-key.pem"
PCR_PUBLIC="/etc/systemd/tpm2-pcr-public-key.pem"
PCR_SIGNATURE="/etc/systemd/tpm2-pcr-signature.json"

# these are common across different distros, you probably don't need to change these
OSREL="/usr/lib/os-release"
EFISTUB="/usr/lib/systemd/boot/efi/linuxx64.efi.stub"

OUTPUT=""

handle_errors() {
    [ "$1" -eq "0" ] && return

    echo "$OUTPUT"
    exit "$1"
}

set +e

OUTPUT+=$(/usr/lib/systemd/systemd-measure sign \
    --linux="$LINUX" \
    --osrel="$OSREL" \
    --cmdline="$CMDLINE" \
    --initrd=<(cat /boot/*-ucode.img "$INITRD") \
    --pcrpkey="$PCR_PUBLIC" \
    --private-key="$PCR_PRIVATE" \
    --public-key="$PCR_PUBLIC" \
    --bank=sha1 \
    --bank=sha256 2>&1)

handle_errors "$?"

printf "%s" "$OUTPUT" > "$PCR_SIGNATURE"

OUTPUT=$(mkdir -p /efi/EFI/Linux && \
    objcopy \
        --add-section .osrel="$OSREL" --change-section-vma .osrel=0x20000 \
        --add-section .cmdline="$CMDLINE" --change-section-vma .cmdline=0x30000 \
        --add-section .linux="$LINUX" --change-section-vma .linux=0x2000000 \
        --add-section .initrd=<(cat /boot/*-ucode.img "$INITRD") --change-section-vma .initrd=0x3000000 \
        --add-section .pcrsig="$PCR_SIGNATURE" --change-section-vma .pcrsig=0x80000 \
        --add-section .pcrpkey="$PCR_PUBLIC" --change-section-vma .pcrpkey=0x90000 \
        "$EFISTUB" \
        "$EFI" 2>&1)

handle_errors "$?"

OUTPUT+=$(sbsign \
    --key "$SB_KEY" \
    --cert "$SB_CERT" \
    --output "$EFI" \
    "$EFI" 2>&1)

handle_errors "$?"
