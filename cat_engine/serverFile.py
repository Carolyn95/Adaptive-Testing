from collections import Counter
import numpy as np
import jsonpickle
import jsonpickle.ext.numpy as jsonpickle_numpy
import math
import random

from catsim.cat import generate_item_bank
# initialization package contains different initial proficiency estimation strategies
from catsim.initialization import *
# selection package contains different item selection strategies
from catsim.selection import *
# estimation package contains different proficiency estimation methods
from catsim.estimation import *
# stopping package contains different stopping criteria for the CAT
from catsim.stopping import *
from flask import request, url_for, jsonify
from flask_api import FlaskAPI, status, exceptions

app = FlaskAPI(__name__)

# to eliminate the error
jsonpickle_numpy.register_handlers()


class ItemResponseTheoryModel:
  #question bank is array of tuple [(question:Object, hardness:0.0 to 1.0)]
  #parameter_model is either '1PL', '2PL', '3PL' or '4PL'
  def __init__(self, question_bank, parameter_model='1PL'):
    self.question_bank = question_bank
    self.question_bank_size = len(self.question_bank)
    assert self.question_bank_size > 0
    assert len(self.question_bank[0]) == 2
    self.indexed_items = generate_item_bank(self.question_bank_size,
                                            itemtype=parameter_model)
    self.parameter_model = parameter_model
    self.initializer = RandomInitializer(
    )  # change default, should use normal distribution and range should fit the difficulty level?
    # self.selector = MaxInfoSelector()
    self.selector = ConditionedMaxInfoSelector()
    self.estimator = HillClimbingEstimator()
    # self.stopper = MaxItemStopper(self.question_bank_size) # change default, could use minErrorStopper
    self.stopper = MaxItemStopper(10)
    # change default, could use minErrorStopper
    # self.stopper = MixedStopper(self.question_bank_size/2)
    # self.stopper = MixedStopper(2)
    self.est_theta = self.initializer.initialize(
    )  # change default, customized theta initializer based on age group
    self.responses = []
    self.administered_items = []
    self.question_KPs = []
    self.administered_kps = []
    self.indexed_question_ids = []
    for i in range(len(self.indexed_items)):
      self.indexed_items[i][1] = question_bank[i][1]
    self.exam_result = []
    self.knowledge_point_bank = []
    self.coverage = 0.5

  def setQuestionKnowledgePoints(self, question_KPs):
    self.question_KPs = question_KPs

  def setAdministeredKnowledgePoints(self, administered_kps):
    self.administered_kps.append(administered_kps)

  def setAdministeredQuestionIds(self, question_id):
    self.indexed_question_ids.append(question_id)

  def setKnowledgePointBank(self, first_administered_kp):
    _set_question_KPs = set([_[1] for _ in self.question_KPs])
    _num_sample = int(len(_set_question_KPs) * self.coverage)
    self.knowledge_point_bank = random.sample(_set_question_KPs, _num_sample)
    if first_administered_kp not in self.knowledge_point_bank:
      self.knowledge_point_bank.pop()
      self.knowledge_point_bank.insert(0, first_administered_kp)

  def setAllQuestion(self, allQuestions):
    self.allQuestions = allQuestions

  def getExamResult(self):
    return self.exam_result

  #question_index is integer >= 0
  #answer is a boolean
  def answerQuestionAndEstimate(self, question_index, raw_answer, answer=False):
    assert question_index < self.question_bank_size
    self.responses.append(bool(answer))
    self.administered_items.append(int(question_index))
    new_est = self.estimator.estimate(
        items=self.indexed_items,
        administered_items=self.administered_items,
        response_vector=self.responses,
        est_theta=self.est_theta)
    self.est_theta = new_est
    this_question = self.allQuestions[question_index]
    this_result = {
        'question_id': this_question['question'],
        'difficulty': this_question['difficulty'],
        'knowledge_point': this_question['knowledge_point'],
        'this_theta': self.est_theta,
        'raw_response': raw_answer,
        'answer': 1 if bool(answer) else 0,
    }
    self.exam_result.append(this_result)

  #returns the next best question to ask -> returns tuple (index: integer, question: Object)
  # params adapt to function call, aka, ConditionedMaxInfoSelector here
  def getNextQuestionIndexToAsk(self):
    item_index = self.selector.select(
        items=self.indexed_items,
        administered_items=self.administered_items,
        est_theta=self.est_theta,
        question_kps=self.question_KPs,
        knowledge_point_bank=self.knowledge_point_bank,
        administered_kps=self.administered_kps,
        coverage=self.coverage,
        result_list=self.exam_result)
    return item_index, self.question_bank[item_index]

  # can be called after each question to know if we should stop asking further questions
  # this call is voluntary
  def shouldWeStopAskingQuestions(self):
    # def stop(self, index: int = None, administered_items: numpy.ndarray = None, question_kps: list = None,
    #  administered_kps: list = None, coverage: float = 0.7, **kwargs) -> bool:
    stop = self.stopper.stop(
        administered_items=self.indexed_items[self.administered_items],
        question_kps=self.question_KPs,
        administered_kps=self.administered_kps,
        coverage=self.coverage,
        theta=self.est_theta)
    return stop

  def analyseExamResult(self):
    # exam_result = []
    exam_result = {}
    exam_result['user_responses'] = self.responses
    exam_result['adminitered_knowledpoints'] = self.administered_kps[1:]
    exam_result['question_ids'] = self.indexed_question_ids[1:]
    exam_result['est_theta'] = self.est_theta
    exam_result['question_difficulties'] = [
        self.question_bank[i][1] for i in self.administered_items
    ]
    exam_result['question_marks'] = [
        difficulty * 3 for difficulty in exam_result['question_difficulties']
    ]
    exam_result['user_scores'] = [
        a * b for a, b in zip(exam_result['user_responses'],
                              exam_result['question_marks'])
    ]
    exam_result['final_format'] = [{
        'ques_id': 'xxx',
        'usr_resp': '...',
        'resp_corrn': '0',
        'ques_diff': 0.009,
        'kp': 'kp1',
        'est_theta': 0.0008
    }]
    return exam_result


###################### FLASK APIs ###############################################


class InvalidUsage(Exception):

  def __init__(self, message):
    super(InvalidUsage, self).__init__()
    self.message = message


@app.route("/firstQuestion", methods=['POST'])
def question_first():
  """
    This function will create new object and initialize the parameters for ItemResponseTheoryModel.
    Then created object will call the function getNextQuestionIndexToAsk to get the question.
    Then it will send the question and object(in pickled format so that it can be reused).
    """
  if request.method == 'POST':
    #list of tuples containing questions along with difficulty level
    questionsList = []
    questionsKPs = []
    questions = request.data.get("questions")
    for ques in questions:
      tup = (ques["question"], ques["difficulty"])
      tup_2 = (ques["question"], ques["knowledge_point"])
      questionsList.append(tup)
      questionsKPs.append(tup_2)
    var = ItemResponseTheoryModel(questionsList)
    getQuestion = var.getNextQuestionIndexToAsk()
    while getQuestion[1][1] >= 1 / 3:
      var = ItemResponseTheoryModel(questionsList)
      getQuestion = var.getNextQuestionIndexToAsk()
      continue
    first_administered_kp = questionsKPs[getQuestion[0]][1]
    var.setQuestionKnowledgePoints(questionsKPs)
    var.setAdministeredKnowledgePoints(first_administered_kp)
    var.setKnowledgePointBank(first_administered_kp)
    var.setAdministeredQuestionIds(getQuestion[1][0])
    var.setAllQuestion(questions)
    pickled = jsonpickle.encode(var)
    resp = {
        "object": pickled,
        "index": getQuestion[0],
        "question": getQuestion[1][0],
        "difficulty": getQuestion[1][1],
        "knowledge_point": questionsKPs[getQuestion[0]][1]
    }

    return resp, status.HTTP_200_OK


@app.route("/nextQuestion", methods=['POST'])
def question_next():
  """
    List or create notes.
    """
  if request.method == 'POST':
    pickled = request.data.get("object")
    correct = request.data.get("correct")
    questionIndex = request.data.get("index")
    raw_answer = request.data.get('raw_answer')

    unPickled = jsonpickle.decode(pickled)
    questionsKPs = unPickled.question_KPs

    unPickled.answerQuestionAndEstimate(questionIndex, raw_answer, correct)
    getQuestion = unPickled.getNextQuestionIndexToAsk()
    unPickled.setAdministeredKnowledgePoints(questionsKPs[getQuestion[0]][1])
    unPickled.setAdministeredQuestionIds(getQuestion[1][0])
    rePickled = jsonpickle.encode(unPickled)
    resp = {
        "object": rePickled,
        "index": getQuestion[0],
        "question": getQuestion[1][0],
        "difficulty": getQuestion[1][1],
        "knowledge_point": questionsKPs[getQuestion[0]][1]
    }

    return resp, status.HTTP_200_OK


@app.route("/stopQuestion", methods=['POST'])
def question_stop():
  """
    This endpoint tell us, whether to stop asking questions or not.
    """
  if request.method == 'POST':
    pickled = request.data.get("object")

    unPickled = jsonpickle.decode(pickled)

    boolean = unPickled.shouldWeStopAskingQuestions()
    message = ""
    if boolean:
      # exam_result = unPickled.analyseExamResult()
      # exam_result = unPickled['exam_result']
      exam_result = unPickled.getExamResult()
      # exam_marks = sum(
      #     [exam_result['answer'] * math.ceil(exam_result['difficulty'] * 3)])
      # exam_result['exam_marks'] = exam_marks
      message = "You can stop asking questions."
    else:
      exam_result = ''
      message = "You should not stop asking questions."
    resp = {"stop": boolean, "message": message, "exam_result": exam_result}

    return resp, status.HTTP_200_OK


# @app.route("/analyseResult", methods=['POST'])
# def analyse_result():
#     """
#     This endpoint is for analysing the exam result.
#     """
#     if request.method == 'POST':
#         pickled = request.data.get("object")
#         unPickled = jsonpickle.decode(pickled)
#         exam_result = unPickled.analyseExamResult()
#         print(exam_result)
#         # rePickled = jsonpickle.encode(exam_result)

#         # resp = {"exam_result": rePickled}
#         return exam_result, status.HTTP_200_OK


#Error handling
@app.errorhandler(404)
def page_not_found(e):
  return {"message": "Enter the correct url for endpoint."}, 404


@app.errorhandler(405)
def page_not_found(e):
  return {"message": "Type of http request is incorrect."}, 405


@app.errorhandler(500)
def page_not_found(e):
  return {
      "message":
          "Internal server error encountered. Pass the parameters in correct format."
  }, 500


if __name__ == "__main__":
  app.run(host='127.0.0.1', port=5000, debug=False)
