export const FPS = 30;
export const TRANSITION = 15; // 0.5초 페이드

// 씬 길이 = (나레이션초 × FPS + (씬수−1) × TRANSITION) ÷ 씬수
// 전환이 겹치는 만큼을 더해줘야 전체 길이가 나레이션과 맞는다.
// 올림해서 영상이 음성보다 아주 조금 길게 끝나도록 한다 (마지막 말이 잘리지 않게).
export const sceneDuration = (narrationSeconds: number, sceneCount: number) =>
  Math.ceil((narrationSeconds * FPS + (sceneCount - 1) * TRANSITION) / sceneCount);

export const totalDuration = (narrationSeconds: number, sceneCount: number) =>
  sceneDuration(narrationSeconds, sceneCount) * sceneCount -
  (sceneCount - 1) * TRANSITION;
