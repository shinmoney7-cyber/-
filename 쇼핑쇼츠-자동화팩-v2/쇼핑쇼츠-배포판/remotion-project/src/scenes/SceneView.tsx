import React from "react";
import {
  AbsoluteFill,
  Img,
  OffthreadVideo,
  staticFile,
  useCurrentFrame,
  interpolate,
} from "remotion";
import type { Scene } from "../schema";

// 헤드라인 없이 영상만 깐다. 자막은 ProductShort의 전역 트랙이 담당한다.
export const SceneView: React.FC<{ scene: Scene; accent: string }> = ({
  scene,
  accent,
}) => {
  const frame = useCurrentFrame();

  // Ken Burns 줌 (미디어가 이미지일 때)
  const zoom = interpolate(frame, [0, 90], [1.06, 1.16], {
    extrapolateRight: "clamp",
  });

  const hasClip = !!scene.clip;
  const hasImage = !!scene.image;

  return (
    <AbsoluteFill>
      {/* 배경 그라디언트 (미디어 없을 때 대비) */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(120% 80% at 50% 20%, ${accent}22, #0b0b0f 60%)`,
        }}
      />

      {/* 미디어 레이어 */}
      <AbsoluteFill style={{ transform: `scale(${hasClip ? 1 : zoom})` }}>
        {hasClip ? (
          <OffthreadVideo
            src={staticFile(scene.clip!)}
            muted
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        ) : hasImage ? (
          <Img
            src={staticFile(scene.image!)}
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        ) : null}
      </AbsoluteFill>

      {/* 하단 어둡게 (자막 가독성) */}
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(to bottom, rgba(0,0,0,0) 45%, rgba(0,0,0,0.6) 100%)",
        }}
      />
    </AbsoluteFill>
  );
};
