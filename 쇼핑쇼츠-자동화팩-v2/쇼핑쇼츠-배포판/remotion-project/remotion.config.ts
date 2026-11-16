import { Config } from "@remotion/cli/config";

// 세로 쇼츠 = 1080x1920, 30fps
Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
Config.setConcurrency(1);
