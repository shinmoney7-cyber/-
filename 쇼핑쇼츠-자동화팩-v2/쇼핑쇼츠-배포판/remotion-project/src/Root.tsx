import { Composition } from "remotion";
import { ProductShort } from "./ProductShort";
import { FPS, totalDuration } from "./timing";
import { productSchema } from "./schema";
import productData from "./data/product.json";

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="ProductShort"
      component={ProductShort}
      durationInFrames={totalDuration(
        productData.narrationDuration,
        productData.scenes.length
      )}
      fps={FPS}
      width={1080}
      height={1920}
      schema={productSchema}
      defaultProps={productData as any}
      calculateMetadata={({ props }) => ({
        durationInFrames: totalDuration(
          props.narrationDuration,
          props.scenes.length
        ),
      })}
    />
  );
};
