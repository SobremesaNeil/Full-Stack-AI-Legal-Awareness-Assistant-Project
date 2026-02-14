import MarkdownIt from 'markdown-it'
import { katex } from '@mdit/plugin-katex'
import 'katex/dist/katex.css'

// 创建 markdown-it 实例
const md = new MarkdownIt({
  html: true,        // 启用 HTML 标签
  breaks: false,     // 不自动转换换行符为 <br>
  linkify: true,     // 自动转换 URL 为链接
  typographer: true, // 启用一些语言中性的替换和引号美化
})

// 配置换行符的处理
md.set({
  breaks: false,
})

// 使用 KaTeX 插件
md.use(katex)

export default md 