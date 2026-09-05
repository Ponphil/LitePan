<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

/**
 * 跨盘秒传 · 秒传航线图（卡片节点版）
 * 左列 = 源盘卡片、右列 = 目标盘卡片，可达线路画成流动虚线"航线"。
 * 交互两段式：点左侧源卡片锁定（其出线点亮、右侧可达卡片亮起），再点右侧可达卡片
 * 完成选中；也可直接点击航线。选中态仍为虚线流动（更亮更粗），不是实线直连。
 */
interface PanMeta {
  driver: string;
  name: string;
  logo: string;
  color: string;
}
interface AirRoute {
  id: string;
  from: PanMeta;
  to: PanMeta;
  method: string;
  method_label: string;
  bidirectional: boolean;
}

const props = defineProps<{
  routes: AirRoute[];
  selectedId: string | null;
  selectedDir: { from: string; to: string } | null;
}>();
const emit = defineEmits<{ select: [route: AirRoute, reversed: boolean]; reselect: [] }>();

const holderRef = ref<HTMLElement | null>(null);
const cw = ref(760);
const compact = ref(false);
const srcLock = ref("");
const hoverKey = ref("");

const nodes = computed(() => {
  const out: string[] = [];
  for (const r of props.routes) {
    for (const k of [r.from.driver, r.to.driver]) {
      if (!out.includes(k)) out.push(k);
    }
  }
  return out;
});

function panOf(k: string): PanMeta {
  for (const r of props.routes) {
    if (r.from.driver === k) return r.from;
  }
  for (const r of props.routes) {
    if (r.to.driver === k) return r.to;
  }
  return { driver: k, name: k, logo: "", color: "#64748b" };
}

interface Pair {
  route: AirRoute;
  f: string;
  t: string;
  reversed: boolean;
}
const pairOf = (r: AirRoute, f: string, t: string): Pair => ({ route: r, f, t, reversed: false });
const keyOf = (p: Pair) => p.f + ">" + p.t;

function pairsFrom(k: string): Pair[] {
  const out: Pair[] = [];
  for (const r of props.routes) {
    if (r.from.driver === k) out.push({ route: r, f: k, t: r.to.driver, reversed: false });
    else if (r.bidirectional && r.to.driver === k) {
      out.push({ route: r, f: k, t: r.from.driver, reversed: true });
    }
  }
  return out;
}
const allForward = () => props.routes.map((r) => pairOf(r, r.from.driver, r.to.driver));

const selectedRoute = computed(() => props.routes.find((r) => r.id === props.selectedId) || null);

/* —— 几何 —— */
const ROW_GAP = 64;
const PAD_Y = 30;
const DESKTOP_CARD_W = 168;
const COMPACT_CARD_W = 132;
const COMPACT_CARD_GAP = 16;
const COMPACT_EDGE_GAP = 4;
const cardWidth = computed(() => {
  if (!compact.value) return DESKTOP_CARD_W;
  const available = cw.value - COMPACT_CARD_GAP - COMPACT_EDGE_GAP * 2;
  return Math.min(COMPACT_CARD_W, Math.max(96, available / 2));
});
const XL = computed(() => compact.value ? cardWidth.value / 2 + COMPACT_EDGE_GAP : 104);
const XR = computed(() => {
  if (compact.value) return cw.value - cardWidth.value / 2 - COMPACT_EDGE_GAP;
  return Math.max(XL.value + 260, cw.value - 104);
});
const yOf = (i: number) => PAD_Y + i * ROW_GAP;
const ch = computed(() => PAD_Y * 2 + (Math.max(2, nodes.value.length) - 1) * ROW_GAP);

interface Geom {
  p: Pair;
  d: string;
  mid: { x: number; y: number };
}

const canTo = (from: string, to: string) => pairsFrom(from).some((p) => p.t === to);
function geom(p: Pair): Geom {
  const i1 = Math.max(0, nodes.value.indexOf(p.f));
  const i2 = Math.max(0, nodes.value.indexOf(p.t));
  // 卡片以 (XL/XR, yOf) 为中心；连线从卡片左/右边缘的垂直中线出发
  const y1 = yOf(i1);
  const y2 = yOf(i2);
  // 端点贴卡片外边缘，不进入卡片框内
  const a = { x: XL.value + cardWidth.value / 2, y: y1 };
  const b = { x: XR.value - cardWidth.value / 2, y: y2 };
  const bend = 34 + (Math.abs(i1 - i2) % 4) * 16;
  const horizontalGap = Math.max(0, b.x - a.x);
  const curve = Math.min(bend * 1.6, Math.max(6, horizontalGap * 0.44));
  const c1x = a.x + curve;
  const c2x = b.x - curve;
  const d = `M ${a.x} ${a.y} C ${c1x} ${a.y}, ${c2x} ${b.y}, ${b.x} ${b.y}`;
  return { p, d, mid: { x: (c1x + c2x) / 2, y: (a.y + b.y) / 2 } };
}

const display = computed<{ g: Geom; level: "base" | "active" | "sel" }[]>(() => {
  if (srcLock.value) {
    return pairsFrom(srcLock.value).map((p) => ({ g: geom(p), level: "active" as const }));
  }
  const dir = props.selectedDir;
  const sr = selectedRoute.value;
  if (dir && sr) {
    return [{ g: geom(pairOf(sr, dir.from, dir.to)), level: "sel" as const }];
  }
  return allForward().map((p) => ({ g: geom(p), level: "base" as const }));
});

const hovered = computed(() => {
  if (!hoverKey.value) return null;
  // 已锁定源或已选中线路：不再响应其它航线的 hover（避免已选线被淡化/打断）
  if (srcLock.value || props.selectedDir) return null;
  const hit = allForward().find((p) => keyOf(p) === hoverKey.value);
  if (!hit) return null;
  return hit;
});
// 仅在“确有另一条线正在被 hover”时才淡化其它线；守卫命中（锁定/已选）或已移除悬停时不做淡化
const hoverDim = computed(() => Boolean(hoverKey.value && hovered.value));

function clickLeft(k: string) {
  if (srcLock.value === k) {
    srcLock.value = "";
    return;
  }
  if (!srcLock.value && props.selectedDir) emit("reselect");
  if (pairsFrom(k).length > 0) srcLock.value = k;
}
function clickRight(k: string) {
  if (!srcLock.value) return;
  const hit = pairsFrom(srcLock.value).find((p) => p.t === k);
  if (hit) {
    srcLock.value = "";
    emit("select", hit.route, hit.reversed);
  }
}
function clickRoute(p: Pair) {
  if (srcLock.value || props.selectedDir) return;
  emit("select", p.route, p.reversed);
}
function sideState(side: "L" | "R", k: string): string {
  const dir = props.selectedDir;
  const isEnd =
    !srcLock.value && dir && ((side === "L" && dir.from === k) || (side === "R" && dir.to === k));
  if (srcLock.value) {
    if (side === "L") return srcLock.value === k ? "on" : "off";
    return canTo(srcLock.value, k) ? "reach" : "off";
  }
  return isEnd ? "on" : "idle";
}
const radarStyle = computed(() => {
  const r = Math.round(Math.min(cw.value, ch.value) * 0.44)
  return {
    width: r * 2 + 'px',
    height: r * 2 + 'px',
    left: '50%',
    top: '50%',
  }
})
function tipStyle(p: Pair) {
  const g = geom(p);
  return { left: g.mid.x + "px", top: g.mid.y + "px" };
}

function measure() {
  if (holderRef.value) {
    cw.value = Math.max(1, holderRef.value.clientWidth);
    compact.value = holderRef.value.clientWidth < 560;
  }
}
let ro: ResizeObserver | null = null;
onMounted(() => {
  measure();
  ro = new ResizeObserver(measure);
  if (holderRef.value) ro.observe(holderRef.value);
});
onBeforeUnmount(() => ro?.disconnect());

const logoFailed = ref<Record<string, boolean>>({});
function markLogoFailed(k: string) {
  logoFailed.value = { ...logoFailed.value, [k]: true };
}
</script>

<template>
  <div ref="holderRef" class="air" :class="{ 'air-c': compact }">
    <div class="air-stage" :style="{ height: `${ch}px` }">
      <div class="air-radar" :style="radarStyle" aria-hidden="true">
        <span class="ar-sweep" />
      </div>
      <svg :viewBox="`0 0 ${cw} ${ch}`" preserveAspectRatio="none" class="air-svg">
        <defs>
          <pattern id="air-grid" width="44" height="44" patternUnits="userSpaceOnUse">
            <path d="M 44 0 L 0 0 0 44" fill="none" stroke="rgba(120,150,220,.07)" stroke-width="1" />
          </pattern>
        </defs>
        <rect :width="cw" :height="ch" fill="url(#air-grid)" />
      </svg>

      <svg :viewBox="`0 0 ${cw} ${ch}`" preserveAspectRatio="none" class="air-lines">
        <path
          v-for="(it, i) in display"
          :key="'d' + i"
          :d="it.g.d"
          class="air-line"
          :class="[
            it.g.p.route.method === 'sha1' ? 'sha1' : 'md5',
            it.g.p.route.bidirectional ? 'bi' : '',
            it.level,
            { hover: hovered && it.g.p.f === hovered.f && it.g.p.t === hovered.t, dim: hoverDim && !(hovered && it.g.p.f === hovered.f && it.g.p.t === hovered.t) },
          ]"
          :stroke="panOf(it.g.p.t).color"
        />
      </svg>

      <svg v-if="!srcLock && !selectedDir" :viewBox="`0 0 ${cw} ${ch}`" preserveAspectRatio="none" class="air-hits">
        <path
          v-for="r in props.routes"
          :key="'h' + r.id"
          :d="geom(pairOf(r, r.from.driver, r.to.driver)).d"
          class="air-hit"
          @mouseenter="hoverKey = r.from.driver + '>' + r.to.driver"
          @mouseleave="hoverKey = ''"
          @click="clickRoute(pairOf(r, r.from.driver, r.to.driver))"
        />
      </svg>

      <!-- 左列源卡片：圆点 · 图标 · 名称 -->
      <div
        v-for="(k, i) in nodes"
        :key="'L' + k"
        class="air-card L"
        :class="sideState('L', k)"
        :style="{ left: `${XL}px`, top: `${yOf(i)}px`, width: `${cardWidth}px` }"
        @click="clickLeft(k)"
      >
        <span class="ac-jack" />
        <span v-if="panOf(k).logo && !logoFailed[k]" class="ac-ic"><img :src="panOf(k).logo" :alt="panOf(k).name" @error="markLogoFailed(k)" /></span>
        <span v-else class="ac-ic ac-fb">{{ panOf(k).name.slice(0, 2) }}</span>
        <span class="ac-nm">{{ panOf(k).name }}</span>
      </div>

      <!-- 右列目标卡片：名称 · 图标 · 圆点（圆点在外侧，与左列镜像） -->
      <div
        v-for="(k, i) in nodes"
        :key="'R' + k"
        class="air-card R"
        :class="sideState('R', k)"
        :style="{ left: `${XR}px`, top: `${yOf(i)}px`, width: `${cardWidth}px` }"
        @click="clickRight(k)"
      >
        <span class="ac-nm">{{ panOf(k).name }}</span>
        <span v-if="panOf(k).logo && !logoFailed[k]" class="ac-ic"><img :src="panOf(k).logo" :alt="panOf(k).name" @error="markLogoFailed(k)" /></span>
        <span v-else class="ac-ic ac-fb">{{ panOf(k).name.slice(0, 2) }}</span>
        <span class="ac-jack" />
      </div>

      <div v-if="hovered" class="air-tip" :style="tipStyle(hovered)">
        <i class="fas fa-plane-departure"></i>{{ panOf(hovered.f).name }} → {{ panOf(hovered.t).name
        }}<span>{{ hovered.route.method_label }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.air {
  width: 100%;
}
.air-stage {
  position: relative;
  overflow: hidden;
}
.air-radar {
  position: absolute;
  transform: translate(-50%, -50%);
  border-radius: 50%;
  pointer-events: none;
  z-index: 0;
  overflow: hidden;
  opacity: 0.9;
}
/* 无圆盘、无边框：仅一道绿色扫描扇，尾部渐隐自然融入背景 */
.ar-sweep {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background: conic-gradient(
    from 0deg,
    rgba(74, 222, 128, 0) 0deg,
    rgba(74, 222, 128, 0.28) 12deg,
    rgba(74, 222, 128, 0.1) 34deg,
    rgba(74, 222, 128, 0) 70deg
  );
  animation: air-scan 6s linear infinite;
}
.air-radar::after {
  content: "";
  position: absolute;
  left: 50%;
  top: 50%;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  background: rgba(74, 222, 128, 0.9);
  box-shadow: 0 0 8px 2px rgba(74, 222, 128, 0.45);
}
@keyframes air-scan {
  to {
    transform: rotate(360deg);
  }
}
/* 注：不在 prefers-reduced-motion 下停掉雷达扇。它是纯装饰光效，
   停掉会残留一个 0° 起始的残缺扇形（Windows 减弱动画开启时的观感），
   且与同屏仍在流动的航线虚线不一致，故保持与 air-flow 相同的策略。 */
.air-svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}
.air-lines {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  overflow: visible;
}
/* 航线始终是虚线流动；选中=更亮更粗的流动虚线，非实线 */
.air-line {
  fill: none;
  stroke-width: 2;
  stroke-linecap: round;
  opacity: 0.32;
  stroke-dasharray: 7 9;
  animation: air-flow 1.6s linear infinite;
}
.air-line.sha1 {
  stroke-dasharray: 1 8;
  opacity: 0.4;
}
.air-line.bi {
  stroke-dasharray: 2 7;
}
.air-line.active {
  opacity: 0.92;
  stroke-width: 2.6;
}
.air-line.sel {
  opacity: 1;
  stroke-width: 3.4;
  animation-duration: 0.9s;
  filter: drop-shadow(0 0 9px currentColor);
}
.air-line.hover {
  opacity: 1;
  stroke-width: 3;
  filter: drop-shadow(0 0 8px currentColor);
}
.air-line.dim {
  opacity: 0.06;
  animation: none;
}
@keyframes air-flow {
  to {
    stroke-dashoffset: -64;
  }
}
.air-hits {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}
.air-hit {
  fill: none;
  stroke: transparent;
  stroke-width: 12;
  pointer-events: stroke;
  cursor: pointer;
}

/* —— 卡片节点 —— */
.air-card {
  position: absolute;
  transform: translate(-50%, -50%);
  display: flex;
  align-items: center;
  gap: 8px;
  width: 168px;
  height: 44px;
  padding: 0 9px;
  border-radius: 9px;
  cursor: pointer;
  background: rgba(16, 28, 54, 0.6);
  border: 1px solid rgba(140, 170, 255, 0.22);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.25);
  transition: border-color 0.15s, box-shadow 0.15s, background 0.15s, opacity 0.15s;
  z-index: 3;
}
.air-card.R {
  flex-direction: row;
}
.air-card:hover {
  border-color: rgba(140, 170, 255, 0.55);
  background: rgba(22, 36, 66, 0.75);
}
.air-card.on {
  border-color: rgba(34, 197, 94, 0.9);
  background: rgba(34, 197, 94, 0.12);
  box-shadow:
    0 0 0 2px rgba(34, 197, 94, 0.28),
    0 0 18px rgba(34, 197, 94, 0.35);
}
.air-card.reach {
  border-color: rgba(140, 170, 255, 0.75);
  box-shadow:
    0 0 0 2px rgba(140, 170, 255, 0.2),
    0 0 16px rgba(140, 170, 255, 0.3);
}
.air-card.off {
  opacity: 0.28;
  filter: saturate(0.3);
}
.ac-jack {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #0b1730;
  border: 2.5px solid rgba(140, 170, 255, 0.45);
  flex: none;
}
.air-card.on .ac-jack {
  border-color: #22c55e;
  box-shadow: 0 0 8px #22c55e;
}
.air-card.reach .ac-jack {
  border-color: rgba(160, 185, 255, 0.9);
}
.ac-ic {
  width: 22px;
  height: 22px;
  flex: none;
  display: grid;
  place-items: center;
}
.ac-ic img {
  width: 22px;
  height: 22px;
  object-fit: contain;
  border-radius: 5px;
}
.ac-fb {
  border-radius: 50%;
  background: var(--brand, #4c74df);
  color: #fff;
  font-size: 9px;
  font-weight: 800;
}
.ac-nm {
  flex: 1;
  min-width: 0;
  font-size: 12px;
  font-weight: 700;
  color: #dbe6ff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.air-card.R .ac-nm {
  text-align: right;
}
.air-card.on .ac-nm {
  color: #eafff4;
}

.air-tip {
  position: absolute;
  transform: translate(-50%, -130%);
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(13, 27, 51, 0.96);
  border: 1px solid rgba(140, 170, 255, 0.4);
  color: #e8eeff;
  font-size: 12px;
  font-weight: 650;
  white-space: nowrap;
  box-shadow: 0 10px 26px rgba(0, 0, 0, 0.45);
  pointer-events: none;
  z-index: 6;
}
.air-tip i {
  color: #8fb0ff;
}
.air-tip span {
  color: #8fa0c4;
  font-weight: 500;
  margin-left: 4px;
}

/* 窄窗紧凑：卡片宽度由可用空间动态计算，文字截断防叠 */
.air-c .ac-nm {
  font-size: 11px;
}
</style>
