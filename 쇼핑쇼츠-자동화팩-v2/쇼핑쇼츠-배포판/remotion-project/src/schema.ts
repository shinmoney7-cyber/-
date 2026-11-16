import { z } from "zod";

export const sceneSchema = z.object({
  type: z.enum(["hook", "feature", "cta"]),
  clip: z.string().optional(),
  image: z.string().optional(),
});

// 나레이션 음성에서 실측한 자막 한 줄. start는 오디오 시작 기준 초.
export const captionSchema = z.object({
  text: z.string(),
  start: z.number(),
});

export const productSchema = z.object({
  brand: z.string(),
  productName: z.string(),
  coupangUrl: z.string(),
  accent: z.string(),
  bgm: z.string().optional(),
  narrationDuration: z.number(),
  captions: z.array(captionSchema),
  scenes: z.array(sceneSchema),
});

export type Product = z.infer<typeof productSchema>;
export type Scene = z.infer<typeof sceneSchema>;
export type Caption = z.infer<typeof captionSchema>;
