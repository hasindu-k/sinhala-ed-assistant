# app/utils/numbering.py

from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


def generate_display_numbering(sub_questions: List[Dict[str, Any]], parent_prefix: str = "") -> List[Dict[str, Any]]:
    """
    Generate display numbering like 1(a)(i) dynamically from hierarchical structure.
    Never stores numbering text - reconstructs it from DB hierarchy.

    Args:
        sub_questions: List of sub-question dicts with hierarchical structure
        parent_prefix: Prefix from parent levels (e.g., "1(a)")

    Returns:
        List of sub-questions with display_numbering added
    """
    result = []

    for i, sq in enumerate(sub_questions, 1):
        # Build current level numbering
        if parent_prefix:
            current_numbering = f"{parent_prefix}({sq.get('label', str(i))})"
        else:
            current_numbering = sq.get('label', str(i))

        # Create copy with display numbering
        sq_with_numbering = dict(sq)
        sq_with_numbering['display_numbering'] = current_numbering

        # Recursively process children
        if sq.get('children'):
            sq_with_numbering['children'] = generate_display_numbering(
                sq['children'],
                current_numbering
            )

        result.append(sq_with_numbering)

    return result


def get_leaf_sub_questions(sub_questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract only leaf-level sub-questions (those with no children) from hierarchical structure.

    Args:
        sub_questions: Hierarchical sub-question structure

    Returns:
        List of leaf sub-questions only
    """
    leaves = []

    def traverse(node):
        if not node.get('children'):
            leaves.append(node)
        else:
            for child in node['children']:
                traverse(child)

    for sq in sub_questions:
        traverse(sq)

    return leaves