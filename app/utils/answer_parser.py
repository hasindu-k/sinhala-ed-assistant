# app/utils/answer_parser.py

import re
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class AnswerNode:
    """Represents a node in the answer hierarchy tree."""

    def __init__(self, label: str, text: str = "", children: List['AnswerNode'] = None):
        self.label = label
        self.text = text
        self.children = children or []

    def add_child(self, child: 'AnswerNode'):
        self.children.append(child)

    def is_leaf(self) -> bool:
        return len(self.children) == 0

    def get_all_leaves(self) -> List['AnswerNode']:
        """Get all leaf nodes in this subtree."""
        if self.is_leaf():
            return [self]

        leaves = []
        for child in self.children:
            leaves.extend(child.get_all_leaves())
        return leaves


def parse_answer_text(raw_text: str) -> Dict[str, str]:
    """
    Parse OCR text to build temporary recursive answer structure.
    Extracts only leaf-level answers and returns {sub_question_id → answer_text}.

    This replaces the old build_numbered_answers function.

    Args:
        raw_text: Raw OCR text from answer script

    Returns:
        Dict mapping sub_question_id to answer text (only leaf nodes)
    """
    if not raw_text:
        return {}

    # Clean and split text
    lines = [line.strip() for line in raw_text.split('\n') if line.strip()]

    # Build hierarchical answer tree
    root = AnswerNode("root")
    current_path = [root]  # Stack to track current hierarchy level

    # Patterns for detecting answer markers
    main_pattern = re.compile(r'^(\d+)\.?$')  # 1., 2., etc.
    sub_pattern = re.compile(r'^([a-zA-Z]|i{1,3}|iv|v)[\.\)]?\s*(.*)$')  # a), i), etc.

    buffer = []

    def save_current_answer():
        """Save accumulated text to current node."""
        if buffer and current_path:
            current_node = current_path[-1]
            current_node.text = '\n'.join(buffer).strip()
            buffer.clear()

    for line in lines:
        # Check for main question marker
        main_match = main_pattern.match(line)
        if main_match:
            save_current_answer()
            # For main questions, we create a placeholder node
            # In practice, main questions don't have answers directly
            continue

        # Check for sub-question marker
        sub_match = sub_pattern.match(line)
        if sub_match:
            save_current_answer()

            marker = sub_match.group(1)
            remaining_text = sub_match.group(2).strip()

            # Determine hierarchy level based on marker type
            level = _determine_hierarchy_level(marker)

            # Adjust path to correct level
            while len(current_path) > level + 1:  # +1 because root is level 0
                current_path.pop()

            # Create new node
            new_node = AnswerNode(marker, remaining_text)

            # Add to parent
            if len(current_path) > 1:  # Not root
                current_path[-1].add_child(new_node)

            current_path.append(new_node)
        else:
            # Continue accumulating text for current answer
            buffer.append(line)

    save_current_answer()

    # For now, return empty dict as we need to map to actual sub_question_ids
    # This will be done in the evaluation service
    return {}


def _determine_hierarchy_level(marker: str) -> int:
    """
    Determine hierarchy level based on marker type.
    This is a heuristic - may need adjustment based on actual exam patterns.

    Returns:
        0: Main question (shouldn't happen in answers)
        1: First level sub-questions (a, b, c, A, B, C)
        2: Second level (i, ii, iii, iv, v)
        3+: Deeper levels
    """
    if marker.isalpha():
        if marker.isupper():
            return 1  # A, B, C
        else:
            return 1  # a, b, c
    elif marker in ['i', 'ii', 'iii', 'iv', 'v']:
        return 2  # Roman numerals
    else:
        return 1  # Default


def map_answers_to_sub_questions(
    parsed_answers: Dict[str, str],
    sub_question_hierarchy: List[Dict[str, Any]]
) -> Dict[str, str]:
    """
    Map parsed answers to actual sub_question_ids.
    This is a placeholder - actual implementation would depend on how
    the answer parsing identifies which sub-question each answer belongs to.

    Args:
        parsed_answers: Dict from parse_answer_text (currently empty)
        sub_question_hierarchy: Hierarchical sub-question structure

    Returns:
        Dict mapping sub_question_id to answer_text
    """
    # This is a simplified implementation
    # In practice, you'd need more sophisticated logic to match
    # parsed answer markers to the actual sub-question hierarchy

    from app.utils.numbering import get_leaf_sub_questions

    leaf_questions = get_leaf_sub_questions(sub_question_hierarchy)

    # For now, return empty mapping
    # Real implementation would match based on numbering patterns
    return {str(sq['id']): "" for sq in leaf_questions}