import hashlib
from typing import List

class MerkleTree:
    def __init__(self):
        self.leaves: List[str] = []
        self.tree: List[List[str]] = []

    def add_leaf(self, leaf_hash: str):
        """Add a leaf hash to the tree."""
        self.leaves.append(leaf_hash)

    def build(self):
        """Build the Merkle tree from leaves."""
        if not self.leaves:
            return
        
        self.tree = [self.leaves[:]]
        current_level = self.leaves[:]
        
        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                combined = left + right
                parent_hash = hashlib.sha256(combined.encode()).hexdigest()
                next_level.append(parent_hash)
            self.tree.append(next_level)
            current_level = next_level

    def get_root(self) -> str:
        """Get the Merkle root hash."""
        if not self.tree:
            return ""
        return self.tree[-1][0] if self.tree[-1] else ""

    def verify_leaf(self, leaf_hash: str, index: int, root: str) -> bool:
        """Verify if a leaf hash belongs to the tree with the given root."""
        if index >= len(self.leaves):
            return False
        
        current_hash = leaf_hash
        for level in self.tree[:-1]:
            is_left = index % 2 == 0
            sibling_index = index + 1 if is_left else index - 1
            sibling_hash = level[sibling_index] if 0 <= sibling_index < len(level) else current_hash
            combined = current_hash + sibling_hash if is_left else sibling_hash + current_hash
            current_hash = hashlib.sha256(combined.encode()).hexdigest()
            index //= 2
        
        return current_hash == root