

from typing import List


class Quiz_Answer():
    """
    Represents an answer option for a Canvas quiz question.
    """
    text: str
    weight: int

    def __init__(self, text: str, weight: int):
        self.text = text
        self.weight = weight


    def as_json(self):
        return {
            "answer_text": self.text,
            "answer_weight": self.weight
        }
    

class Quiz_Question():
    """
    Represents a question in a Canvas quiz.
    """
    question_type: str
    question_text: str
    points_possible: float
    answers: List[Quiz_Answer]

    def __init__(self, question_type: str, question_text: str, points_possible: float, answers: List[Quiz_Answer]):
        self.id = id
        self.question_type = question_type
        self.question_text = question_text
        self.points_possible = points_possible
        self.answers = answers