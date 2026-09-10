import { Image } from "expo-image";
import { teamHelmetAssets } from "./teamHelmetAssets";

/** Decorative original artwork; the adjacent text supplies the team name. */
export function TeamHelmet({
  team,
  size = 64,
}: {
  team: string;
  size?: number;
}) {
  const abbr = team.trim().toUpperCase();
  const canonical =
    (
      { JAC: "JAX", WSH: "WAS", LA: "LAR", OAK: "LV", SD: "LAC" } as Record<
        string,
        string
      >
    )[abbr] || abbr;
  return (
    <Image
      source={teamHelmetAssets[canonical] || teamHelmetAssets.DEFAULT}
      style={{ width: size, height: size * 0.8, flexShrink: 0 }}
      contentFit="contain"
      accessible={false}
    />
  );
}
