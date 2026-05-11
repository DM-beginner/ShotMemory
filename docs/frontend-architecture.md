# ShotMemory — 前端架构概览

## 1. 服务定位

单一 React SPA，PC 浏览器与移动端浏览器共用一套代码（响应式布局）。所有数据通过 RTK Query 调用后端 `/v1/*`，通过 HTTPOnly Cookie 完成认证，前端不持有任何 token。

---

## 2. 技术选型

| 层级 | 技术 |
|------|------|
| 框架 | React 19 + TypeScript 5.9 |
| 构建 | Vite，由 pnpm `overrides` 替换为 `rolldown-vite@7.2.5`（Rust 加速） |
| 状态管理 | Redux Toolkit + RTK Query |
| 路由 | React Router v7 |
| UI 组件 | HeroUI（`@heroui/react`） |
| 样式 | Tailwind CSS 4（`@tailwindcss/vite`），通过 `@plugin "./hero.ts"` 注入 HeroUI 主题 |
| 主题 | next-themes（`attribute="class"`，`defaultTheme="system"`） |
| 动效 | framer-motion |
| 图标 | lucide-react |
| 瀑布流 | masonic（虚拟化） + react-intersection-observer（哨兵触底） |
| 地图 / 3D 地球 | maplibre-gl + react-map-gl + supercluster + use-supercluster |
| 校验 / 通知 | HeroUI 自带 |

依赖完整列表见 `frontend/package.json`。

---

## 3. 目录结构

```
frontend/
  package.json
  src/
    main.tsx                     # 入口：StrictMode → Provider → Router → HeroUI → ThemeProvider → <App/>
    App.tsx                      # 路由表
    app/
      store.ts                   # configureStore：baseApi.reducer + auth slice
      baseApi.ts                 # createApi + baseQueryWithReauth（401 自动刷新）
      router.ts                  # （空文件占位，路由实际写在 App.tsx）
      baseResponseType.ts        # 共享响应类型
    layouts/
      MainLayout.tsx             # 嵌套路由外壳：<Header/> + <Outlet/>
      Header.tsx                 # 顶部导航（含登录按钮、上传入口、主题切换）
    services/
      auth/
        components/AuthModal.tsx
        redux/api/authApi.ts
        redux/slices/authSlice.ts
        types/authType.ts
        utils/tokenHelper.ts     # device_id 持久化、useAuthCheck hook
        utils/avatarUrl.ts
        index.ts
      photo/
        components/{PhotoWall,PhotoCard,PhotoDetail,UploadModal,ExifPanel,ThumbnailStrip}.tsx
        components/globe/{PhotoGlobe,PhotoGlobePage,ClusterMarker,SingleMarker,useMapClusters,globeStyle}.{ts,tsx}
        redux/api/photoApi.ts
        types/{photoType,globeTypes}.ts
        utils/{photoUrl,exifFormat,globeAdapter}.ts
        index.ts
      story/
        components/{StoryList,StoryDetail,StoryEditor,GalleryPickerModal}.tsx
        redux/api/storyApi.ts
        types/storyType.ts
        index.ts
    styles/
      global.css                 # @import maplibre/tailwind，定义滚动条样式
      hero.ts                    # HeroUI Tailwind plugin 配置
    config/, assets/             # 当前为空
```

按域（`auth` / `photo` / `story`）划分，与后端 `services/` 结构呼应。

> 上述目录树仅作心智模型展示，实际文件以 `frontend/src/` 为准。

---

## 4. 启动流程（`src/main.tsx`）

```tsx
<StrictMode>
  <Provider store={store}>                    {/* 1. Redux 数据仓库 */}
    <BrowserRouter>                            {/* 2. URL 路由 */}
      <HeroUIProviderWithRouter>               {/* 3. HeroUI（注入 react-router 的 navigate） */}
        <NextThemesProvider attribute="class" defaultTheme="system">
          <App />
        </NextThemesProvider>
      </HeroUIProviderWithRouter>
    </BrowserRouter>
  </Provider>
</StrictMode>
```

`<App/>` 顶部调用 `useAuthCheck()`（`services/auth/utils/tokenHelper`），首屏即触发 `GET /v1/auth/me`：

- 成功 → `authSlice.isAuthenticated = true`
- 失败 → 保持未登录，最后 `dispatch(setInitializing(false))` 关闭 loading

---

## 5. 路由表（`src/App.tsx`）

| 路径 | 组件 | 布局 | 用途 |
|------|------|------|------|
| `/`               | `PhotoWall`         | `MainLayout` | 瀑布流首页（默认） |
| `/story`          | `StoryList`         | `MainLayout` | 故事列表 |
| `/story/new`      | `StoryEditor`       | `MainLayout` | 创建故事 |
| `/story/:id`      | `StoryDetail`       | `MainLayout` | 故事详情 |
| `/story/:id/edit` | `StoryEditor`       | `MainLayout` | 编辑故事 |
| `/photo/:id`      | `PhotoDetail`       | （独立全屏） | 单张照片详情、左右切换、EXIF 面板 |
| `/globe`          | `PhotoGlobePage`    | （独立全屏） | 3D 地球展示所有带 GPS 的照片 |
| `*`               | `<Navigate to="/">` | —            | 兜底 |

`MainLayout`（`src/layouts/MainLayout.tsx`）只是 `<Header/> + <Outlet/>` 的极简结构。

---

## 6. 鉴权方案

| 方面 | 设计 |
|------|------|
| Token 存储 | 后端通过 HTTPOnly Cookie 下发，前端**不可访问也不需要访问**。请求经 `credentials: "include"` 自动携带 |
| device_id  | 前端调 `crypto.randomUUID()` 生成，写入 `localStorage["shotmemory_device_id"]`；登录请求体必传 |
| 自动刷新   | `baseQueryWithReauth` 检测 `401 + message=="Token expired"` → `POST /auth/refresh` → 成功重试原请求；失败 `dispatch(authSlice.actions.resetAuth())` |
| 启动恢复   | `useAuthCheck()` 调 `getMe`，成功即 `isAuthenticated = true` |
| 登出       | `POST /auth/logout` 后 `dispatch(baseApi.util.resetApiState())` 清空 RTK 缓存，避免残留照片数据 |

详细 cookie 路径（access `/`、refresh `/v1/auth`）见 [`docs/modules/auth.md`](./modules/auth.md)。

---

## 7. RTK Query 架构

```
src/app/baseApi.ts
  ├─ baseUrl = `${VITE_BACKEND_HOST}${VITE_BACKEND_PREFIX || "/v1"}`
  ├─ credentials: "include"
  ├─ baseQueryWithReauth：401 + Token expired → /auth/refresh → 重试
  └─ tagTypes: ["User", "Auth", "Photo", "Story"]

services/{auth,photo,story}/redux/api/*.ts
  └─ baseApi.injectEndpoints({...})
```

### 7.1 Auth API（`services/auth/redux/api/authApi.ts`）

| Hook | 方法 | Tags |
|------|------|------|
| `useRegisterMutation`     | `POST` | — |
| `useLoginMutation`        | `POST` | invalidates `Auth`, `Photo` |
| `useRefreshTokenMutation` | `POST` | — |
| `useLogoutMutation`       | `POST` | `onQueryStarted` 后 `resetApiState()` |
| `useUploadAvatarMutation` | `PUT`  | invalidates `Auth` |
| `getMe` (lazy)            | `GET`  | provides `Auth` |

### 7.2 Photo API（`services/photo/redux/api/photoApi.ts`）

| Hook | 方法 | Tags |
|------|------|------|
| `useGetMyPhotosQuery({limit, offset})` | `GET`    | provides `Photo` |
| `useGetPhotoQuery(id)`                 | `GET`    | provides `{type:Photo, id}` |
| `useUploadPhotosMutation(File[])`      | `POST` (FormData) | invalidates `Photo` |
| `useUpdatePhotoMutation`               | `PATCH`  | invalidates `{type:Photo, id}` |
| `useDeletePhotoMutation`               | `DELETE` | **不** invalidate（PhotoWall 通过 onDeleted 本地剔除，避免与 Masonry 布局冲突） |
| `useBatchDeletePhotosMutation`         | `POST`   | 同上 |

### 7.3 Story API（`services/story/redux/api/storyApi.ts`）

| Hook | 方法 | Tags |
|------|------|------|
| `useGetMyStoriesQuery`     | `GET`    | provides `Story` |
| `useGetStoryQuery(id)`     | `GET`    | provides `{type:Story, id}` |
| `useCreateStoryMutation`   | `POST`   | invalidates `Story` |
| `useUpdateStoryMutation`   | `PATCH`  | invalidates `Story` |
| `useDeleteStoryMutation`   | `DELETE` | invalidates `Story` |

---

## 8. authSlice（`services/auth/redux/slices/authSlice.ts`）

```ts
{
  isAuthenticated: boolean,    // 由 RTK matchFulfilled / matchRejected 同步
  isInitializing: boolean      // useAuthCheck 完成后置 false
}
```

`extraReducers` 监听：
- `login.matchFulfilled`     → `isAuthenticated = true`
- `login.matchRejected`      → `false`
- `refreshToken.matchFulfilled` → `true`
- `refreshToken.matchRejected`  → `false`
- `logout.matchFulfilled`    → `false`
- `getMe.matchFulfilled`     → `true`
- `getMe.matchRejected`      → `false`

显式 reducers：`setAuthenticated`、`setInitializing`、`setLoading`、`resetAuth`。

---

## 9. 环境变量

| 变量 | 默认 | 说明 |
|------|------|------|
| `VITE_BACKEND_HOST` | `""` | 后端 host（含 protocol），生产需要写完整域名 |
| `VITE_BACKEND_PREFIX` | `/v1` | API 前缀 |
| `VITE_STORAGE_BASE_URL` | `""` | 静态资源前缀。dev = `http://localhost:5683/static`；prod = CDN 域名 |

---

## 10. 图片 URL 拼接约定（`services/photo/utils/photoUrl.ts`）

```ts
getPhotoUrl(photo)    = `${STORAGE_BASE}/${photo.thumbnail_key ?? photo.object_key}`
getOriginalUrl(photo) = `${STORAGE_BASE}/${photo.object_key}`
getVideoUrl(photo)    = photo.video_key ? `${STORAGE_BASE}/${photo.video_key}` : null
```

后端只返回 `object_key`、`thumbnail_key`、`video_key`，前端按需拼接。

---

## 11. 3D 地球（`services/photo/components/globe/`）

```
PhotoGlobePage
  └── PhotoGlobe
        ├─ <Map projection="globe">          ← react-map-gl/maplibre
        ├─ useMapClusters(photos, bounds, zoom)  ← supercluster 包装
        ├─ <ClusterMarker />                  ← 聚合点
        └─ <SingleMarker />                   ← 单张照片
```

- 初始视角：`zoom=2`（见 `PhotoGlobe.tsx`）
- 点击聚合点：`flyTo({zoom: expansionZoom, pitch: 45, duration: 1500})`
- `globeStyle.ts` 定义 globe 投影 + 大气层样式
- `globeAdapter.ts` 将 `Photo[]` 转换成 supercluster 输入格式

---

## 12. 瀑布流（`services/photo/components/PhotoWall.tsx`）

- masonic 自动按容器宽度计算列数 + 虚拟化窗口
- 列表数据来自 `useGetMyPhotosQuery` 分页
- `react-intersection-observer` 哨兵触底加载下一页
- 删除：调 `useDeletePhotoMutation` / `useBatchDeletePhotosMutation` 后通过 `onDeleted(id)` 直接修改本地 photos 状态，**不依赖** RTK 自动 refetch（避免 Masonry 重排闪屏）

---

## 13. 主题与样式

- `next-themes` 通过切换根节点 `class="dark"` 触发 Tailwind `dark:` 变体
- `@custom-variant dark (&:is(.dark *))` 在 `global.css` 定义
- 自定义滚动条仅在 `min-width:1024px` 生效，深浅色区分
- HeroUI 通过 Tailwind 4 plugin 注入（`@plugin "./hero.ts"`）

---

## 14. 与后端的对接约定

| 维度 | 约定 |
|------|------|
| 基础路径 | `/v1` |
| 响应格式 | `{ code: 20000, message: "操作成功", data: T \| null }` |
| 鉴权 | HTTPOnly Cookie，请求加 `credentials: include` |
| 401 处理 | `message == "Token expired"` 才尝试 `/auth/refresh`，其他 401 直接弹回登录 |
| 设备绑定 | 登录请求 body 必传 `device_id`（前端 localStorage） |
| 图片 / 视频 | 后端返回 `object_key` / `thumbnail_key` / `video_key`，前端 `${VITE_STORAGE_BASE_URL}/...` 拼接 |
| 分页 | `?limit=&offset=`，响应含 `total` 与 `items` |
| 状态轮询 | 上传后通过 `useGetPhotoQuery(id)` 轮询 `status`（processing / completed / no_exif） |
