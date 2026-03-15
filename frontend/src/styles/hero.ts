// hero.ts
import { heroui } from "@heroui/react";
export default heroui({
  prefix: "gallery", // 可选：自定义 CSS 变量前缀，防止冲突
  layout: {
    dividerWeight: "1px", // h-divider the default height applied to the divider component
    disabledOpacity: 0.5, // this value is applied as opacity-[value] when the component is disabled
    fontSize: {
      tiny: "0.75rem", // text-tiny
      small: "0.875rem", // text-small
      medium: "1rem", // text-medium
      large: "1.125rem", // text-large
    },
    lineHeight: {
      tiny: "1rem", // text-tiny
      small: "1.25rem", // text-small
      medium: "1.5rem", // text-medium
      large: "1.75rem", // text-large
    },
    radius: {
      small: "8px", // rounded-small
      medium: "12px", // rounded-medium
      large: "14px", // rounded-large
    },
    borderWidth: {
      small: "1px", // border-small
      medium: "2px", // border-medium (default)
      large: "3px", // border-large
    },
  },
  themes: {
    dark: {
      colors: {
        background: "#0a0a0a", // 纯粹的深黑背景，让照片色彩更突出
        foreground: "#ededed", // 柔和的白色文字
        primary: {
          DEFAULT: "#7828C8", // 你的品牌主色调
          foreground: "#ffffff",
        },
      },
      // same as default
      layout: {
        hoverOpacity: 0.9, //  this value is applied as opacity-[value] when the component is hovered
        boxShadow: {
          // shadow-small
          small:
            "0px 0px 5px 0px rgb(0 0 0 / 0.05), 0px 2px 10px 0px rgb(0 0 0 / 0.2), inset 0px 0px 1px 0px rgb(255 255 255 / 0.15)",
          // shadow-medium
          medium:
            "0px 0px 15px 0px rgb(0 0 0 / 0.06), 0px 2px 30px 0px rgb(0 0 0 / 0.22), inset 0px 0px 1px 0px rgb(255 255 255 / 0.15)",
          // shadow-large
          large:
            "0px 0px 30px 0px rgb(0 0 0 / 0.07), 0px 30px 60px 0px rgb(0 0 0 / 0.26), inset 0px 0px 1px 0px rgb(255 255 255 / 0.15)",
        },
      },
    },
    light: {
      colors: {
        // 1. 全局基底色
        background: "#fbfbfe", // 页面的大背景色（纯白）
        foreground: "#000000", // 全局的默认文字颜色（纯黑，确保在白背景上清晰可见）

        // 2. 品牌主色调 (Primary)
        primary: {
          DEFAULT: "#E4D4F4", // 这是主色调本身（这是一个很好看的 Tailwind 默认蓝色 blue-500）
          foreground: "#000000", // ★ 关键点：当一个组件（比如按钮）使用了 primary 颜色作为背景时，它里面的文字该是什么颜色？（这里设定为纯白）
        },
      },
      layout: {
        hoverOpacity: 0.8, //  this value is applied as opacity-[value] when the component is hovered
        boxShadow: {
          // shadow-small
          small:
            "0px 0px 5px 0px rgb(0 0 0 / 0.02), 0px 2px 10px 0px rgb(0 0 0 / 0.06), 0px 0px 1px 0px rgb(0 0 0 / 0.3)",
          // shadow-medium
          medium:
            "0px 0px 15px 0px rgb(0 0 0 / 0.03), 0px 2px 30px 0px rgb(0 0 0 / 0.08), 0px 0px 1px 0px rgb(0 0 0 / 0.3)",
          // shadow-large
          large:
            "0px 0px 30px 0px rgb(0 0 0 / 0.04), 0px 30px 60px 0px rgb(0 0 0 / 0.12), 0px 0px 1px 0px rgb(0 0 0 / 0.3)",
        },
      },
    },
  },
});

/* 
1. hero.ts 是如何作用于全域的？（底层机制）
你在 hero.ts 里写的那些 primary: "#E4D4F4"、radius: "12px"，
在项目运行时，并不会作为 JavaScript 存在。
HeroUI 插件会在 Vite 编译阶段，
将这些配置全部翻译成全局 CSS 变量（CSS Custom Properties），
并悄悄注入到你网页的 <html> 根节点上。
因为你设置了 prefix: "gallery"，所以它在浏览器里实际生成的 CSS 长这样：
:root, [data-theme="light"] {
  --gallery-background: #ffffff;
  --gallery-primary: #E4D4F4;
  --gallery-radius-medium: 12px;
}
.dark {
  --gallery-background: #0a0a0a;
  --gallery-primary: #7828C8;
}
作用域： 既然挂载在了 :root 和 .dark 上，这意味着你整个 React 项目里的任何组件（无论藏得有多深），只要使用了相关的 Tailwind 类名（如 bg-primary、rounded-md），就会自动去读取这些全局变量。这就是它“统御全域”的真相。

*/
