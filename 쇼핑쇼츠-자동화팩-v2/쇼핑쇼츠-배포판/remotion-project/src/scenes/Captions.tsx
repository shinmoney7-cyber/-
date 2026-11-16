import React from "react";
import { useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";
import type { Caption } from "../schema";

// 나레이션에서 실측한 start(초)에 맞춰 자막을 띄운다.
// 씬 경계와 무관한 전역 트랙이라, 씬 길이를 바꿔도 음성과 어긋나지 않는다.
export const Captions: React.FC<{ captions: Caption[]; accent: string }> = ({
  captions,
  accent,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const time = frame / fps;

  let active = -1;
  for (let i = 0; i < captions.length; i++) {
    if (time >= captions[i].start) active = i;
  }
  if (active === -1) return null;

  const localFrame = frame - Math.round(captions[active].start * fps);
  const pop = spring({
    frame: localFrame,
    fps,
    config: { damping: 12, stiffness: 160 },
    durationInFrames: 12,
  });
  const scale = interpolate(pop, [0, 1], [0.82, 1]);

  return (
    <div
      style={{
        position: "absolute",
        bottom: 420,
        width: "100%",
        textAlign: "center",
        padding: "0 60px",
      }}
    >
      <span
        style={{
          display: "inline-block",
          transform: `scale(${scale})`,
          opacity: pop,
          background: "rgba(0,0,0,0.62)",
          color: "white",
          fontSize: 58,
          fontWeight: 800,
          padding: "18px 34px",
          borderRadius: 22,
          border: `4px solid ${accent}`,
          lineHeight: 1.3,
          // 한국어가 단어 중간에서 잘리지 않게 어절 단위로만 줄바꿈
          wordBreak: "keep-all",
          boxShadow: "0 10px 40px rgba(0,0,0,0.5)",
        }}
      >
        {captions[active].text}
      </span>
    </div>
  );
};
