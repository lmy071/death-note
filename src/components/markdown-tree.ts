export interface MarkdownTreeNode {
  children: MarkdownTreeNode[]
  id: string
  name: string
  source?: string
  type: 'directory' | 'file'
}

export function buildMarkdownTree(sources: readonly string[]): MarkdownTreeNode[] {
  const root: MarkdownTreeNode[] = []

  for (const source of sources) {
    const segments = source
      .replace(/^\/md\//, '')
      .split('/')
      .map((segment) => decodeURIComponent(segment))
    let branch = root
    let id = ''

    segments.forEach((segment, index) => {
      id = id ? `${id}/${segment}` : segment
      const isFile = index === segments.length - 1
      let node = branch.find((candidate) => candidate.name === segment)

      if (!node) {
        node = {
          children: [],
          id,
          name: isFile ? segment.replace(/\.md$/i, '') : segment,
          source: isFile ? source : undefined,
          type: isFile ? 'file' : 'directory',
        }
        branch.push(node)
      }

      branch = node.children
    })
  }

  const sortNodes = (nodes: MarkdownTreeNode[]) => {
    nodes.sort((left, right) => {
      if (left.type !== right.type) return left.type === 'directory' ? -1 : 1
      return left.name.localeCompare(right.name, 'zh-CN')
    })
    nodes.forEach((node) => sortNodes(node.children))
  }

  sortNodes(root)
  return root
}
