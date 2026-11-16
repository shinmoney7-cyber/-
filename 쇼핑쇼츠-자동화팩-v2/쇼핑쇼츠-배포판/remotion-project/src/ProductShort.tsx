import React from "react";
import { AbsoluteFill, Audio, staticFile } from "remotion";
import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { SceneView } from "./scenes/SceneView";
import { Captions } from "./scenes/Captions";
import { sceneDuration } from "./timing";
import type { Product } from "./schema";

export { FPS, TRANSITION } from "./timing";
import { TRANSITION } from "./timing";

export const ProductShort: React.FC<Product> = (props) => {
  const { scenes, accent, bgm, captions, narrationDuration } = props;
  const dur = sceneDuration(narrationDuration, scenes.length);

  return (
    <AbsoluteFill style={{ backgroundColor: "#0b0b0f", fontFamily: "'Noto Sans CJK KR','Noto Sans KR',sans-serif" }}>
      <TransitionSeries>
        {scenes.map((scene, i) => (
          <React.Fragment key={i}>
            <TransitionSeries.Sequence durationInFrames={dur}>
              <SceneView scene={scene} accent={accent} />
            </TransitionSeries.Sequence>
            {i < scenes.length - 1 ? (
              <TransitionSeries.Transition
                presentation={fade()}
                timing={linearTiming({ durationInFrames: TRANSITION })}
              />
            ) : null}
          </React.Fragment>
        ))}
      </TransitionSeries>

      {/* 자막은 씬 위에 전역으로 얹어, 씬 전환과 무관하게 음성에 붙는다 */}
      <Captions captions={captions} accent={accent} />

      <Audio src={staticFile("audio/vo.mp3")} volume={1} />

      {bgm ? <Audio src={staticFile(bgm)} volume={0.18} /> : null}
    </AbsoluteFill>
  );
};
