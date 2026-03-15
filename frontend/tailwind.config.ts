// tailwind.config.ts (位于根目录)
import type { Config } from "tailwindcss";

const config: Config = {
  // 1. 扫描路径 (极其重要！)
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
    "./node_modules/@heroui/theme/dist/**/*.{js,ts,jsx,tsx}", // 必须包含 HeroUI 的包路径，否则 HeroUI 的样式不会被编译打包
  ],
  
  // 2. 开启基于 class 的暗黑模式 (HeroUI 强依赖这个)
  darkMode: "class",

  // 3. 原生 Tailwind 的扩展 (这里处理与 HeroUI 无关的纯原生配置)
  theme: {
    extend: {
      // 比如：你想给你的照片集引入一款特殊的全局字体，在这里配置，而不是在 hero.ts 里
      fontFamily: {
        sans: ["Inter", "sans-serif"], 
        display: ["Playfair Display", "serif"], // 适合用作高逼格的照片标题
      },
      // 1. 定义关键帧（怎么动）
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0", transform: "translateY(10px)" }, // 从透明且偏下 10px 的位置开始
          "100%": { opacity: "1", transform: "translateY(0)" },  // 回到正常状态
        },
      },
          // 2. 绑定动画名称和时长
      animation: {
        "fade-in": "fadeIn 0.6s cubic-bezier(0.22, 1, 0.36, 1) forwards", // 稍微改用更高级的贝塞尔曲线
      },
    },
  },
};

export default config;

/* 3. 为什么它们不会冲突？
职责隔离：hero.ts 只管 HeroUI 组件长什么样（颜色、阴影、圆角）；
而 theme.extend 管的是原生 Tailwind 工具类的补充（字体、动画、自定义间距等）。
前缀保护 (prefix: "gallery")：这是你走的一招好棋。
因为你加了前缀，HeroUI 生成的底层变量全都是 --gallery-xxx 开头，
这从物理上杜绝了它和 Tailwind 原生变量（如 --tw-bg-opacity）发生冲突的可能性。
总结一下：tailwind.config.ts 是总指挥部，它定义了战场边界（content）和战略（darkMode）；
而 hero.ts 是一支被招募的精锐部队（plugin），带着自己精良的武器（自定义主题色），听从总指挥部的调遣。
 */