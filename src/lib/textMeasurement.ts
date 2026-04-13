import { prepare, layout } from '@chenglou/pretext'

export interface TextMeasurementOptions {
  text: string
  font?: string
  width: number
  lineHeight?: number
}

export interface TextMeasurementResult {
  height: number
  lineCount: number
  exceedsMaxLines: (maxLines: number) => boolean
}

const DEFAULT_FONT = '14px Inter, system-ui, sans-serif'
const DEFAULT_LINE_HEIGHT = 22

/**
 * 测量文本在指定宽度下的高度和行数
 * 使用 pretext 库实现，无需 DOM 操作
 */
export function measureText(options: TextMeasurementOptions): TextMeasurementResult {
  const { text, font = DEFAULT_FONT, width, lineHeight = DEFAULT_LINE_HEIGHT } = options

  if (!text || text.trim() === '') {
    return {
      height: 0,
      lineCount: 0,
      exceedsMaxLines: () => false,
    }
  }

  const prepared = prepare(text, font)
  const { height, lineCount } = layout(prepared, width, lineHeight)

  return {
    height,
    lineCount,
    exceedsMaxLines: (maxLines: number) => lineCount > maxLines,
  }
}

/**
 * 检查文本是否超过指定行数
 */
export function isTextExceedsLines(
  text: string,
  width: number,
  maxLines: number,
  options?: { font?: string; lineHeight?: number }
): boolean {
  const result = measureText({
    text,
    width,
    font: options?.font,
    lineHeight: options?.lineHeight,
  })
  return result.exceedsMaxLines(maxLines)
}
