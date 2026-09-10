# Team helmets

Original Run My Pool side-profile artwork: one consistent helmet shape with
plain abbreviations and team-inspired colors. These are not official team
logos or replicas of individual teams' helmet graphics.

SVG files are editable source; PNG files are bundled for consistent native
rendering without network requests. DEFAULT is the neutral RMP fallback.

Regenerate from the repository root:

    node rmp/mobile/scripts/generate-team-helmets.cjs

The generator uses Sharp from the installed frontend dependencies and writes
a contact sheet to /tmp/rmp-team-helmets-preview.png.
