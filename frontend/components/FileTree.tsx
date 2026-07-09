"use client";

import { TreeNode } from "@/lib/types";

type Props = {
  node: TreeNode;
  depth?: number;
  selectedPath: string | null;
  onSelect: (path: string) => void;
  parentPath?: string;
};

export default function FileTree({ node, depth = 0, selectedPath, onSelect, parentPath = "" }: Props) {
  const fullPath = node.type === "file" ? node.path : parentPath ? `${parentPath}/${node.name}` : node.name;
  const isRoot = depth === 0 && node.type === "dir";

  if (node.type === "file") {
    const isSelected = selectedPath === node.path;
    return (
      <button
        onClick={() => onSelect(node.path)}
        style={{ paddingLeft: `${depth * 1.1 + 0.5}rem` }}
        className={`diff-line w-full text-left py-1 pr-2 text-sm font-mono flex items-center gap-2 ${
          isSelected ? "diff-line-good" : "diff-line-neutral hover:bg-elevated"
        }`}
      >
        <span className="diff-marker text-good">{isSelected ? "+" : " "}</span>
        <span className={isSelected ? "text-ink" : "text-dim"}>{node.name}</span>
        <span className="ml-auto text-xs text-dim">{node.language}</span>
      </button>
    );
  }

  // directory
  const dirRelPath = isRoot ? "" : fullPath;
  const isSelected = !isRoot && selectedPath === dirRelPath;

  return (
    <div>
      {!isRoot && (
        <button
          onClick={() => onSelect(dirRelPath)}
          style={{ paddingLeft: `${depth * 1.1 + 0.5}rem` }}
          className={`diff-line w-full text-left py-1 pr-2 text-sm font-mono flex items-center gap-2 ${
            isSelected ? "diff-line-good" : "diff-line-neutral hover:bg-elevated"
          }`}
        >
          <span className="diff-marker text-accent">{isSelected ? "+" : "▸"}</span>
          <span className={isSelected ? "text-ink" : "text-ink/80"}>{node.name}/</span>
        </button>
      )}
      {node.children.map((child, i) => (
        <FileTree
          key={i}
          node={child}
          depth={isRoot ? depth : depth + 1}
          selectedPath={selectedPath}
          onSelect={onSelect}
          parentPath={dirRelPath}
        />
      ))}
    </div>
  );
}
