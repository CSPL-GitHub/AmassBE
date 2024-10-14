from rest_framework.decorators import api_view
from rest_framework import status
from rest_framework.response import Response
from django.http import JsonResponse
from django.db import IntegrityError
from datetime import datetime
from core.models import Vendor
from pos.models import Department, CoreUserCategory, CoreUser
from sop.models import Question, Answer, FormResponse



@api_view(['GET'])
def get_sop_form_by_department(request):
    try:
        is_admin = request.GET.get('admin')
        department_id = request.GET.get('department_id')
        vendor_id = request.GET.get('vendor_id')

        if not all((is_admin, department_id, vendor_id)):
            raise ValueError
    
        department_id = int(department_id)
        vendor_id = int(vendor_id)
    
        department_instance = Department.objects.filter(pk=department_id).first()
        vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

        if not all((department_instance, vendor_instance)):
            raise ValueError

        question_answers = []
        
        questions = Question.objects.filter(department=department_id, vendor=vendor_id).order_by('question_number')

        if not questions.exists():
            return JsonResponse({"question_answers": question_answers})
            
        if is_admin == 'true':
            counter = 0

            for single_question in questions:
                answer_list = []

                answer_details = Answer.objects.filter(
                    question = single_question.pk,
                    vendor = vendor_id
                ).order_by("answer_sequence_number")
                
                if answer_details.exists():
                    for answer_detail in answer_details:
                        answer_list.append({
                            "id": answer_detail.pk,
                            "counter": counter,
                            "answer_sequence_number": answer_detail.answer_sequence_number,
                            "ui_element": answer_detail.ui_element,
                            "caption": answer_detail.caption,
                            "caption_locale": answer_detail.caption_locale
                        })

                        counter = counter + 1

                is_response_submitted = False
                
                question_response = FormResponse.objects.filter(
                    question = single_question.pk,
                    question__is_response_multiple = False,
                    department = department_id,
                    response_datetime__date = datetime.now().date(),
                    vendor = vendor_id
                ).first()

                if question_response:
                    is_response_submitted = True

                question_answers.append({
                    "id": single_question.pk,
                    "question_number": single_question.question_number,
                    "question": single_question.question,
                    "question_locale": single_question.question_locale,
                    "is_response_multiple": single_question.is_response_multiple,
                    "is_response_submitted": is_response_submitted,
                    "staff_category_id": single_question.staff_category.pk,
                    "answers": answer_list
                })

        elif is_admin == 'false':
            question_id = request.GET.get('question_id')
            response_date = request.GET.get('date')

            if (not response_date) or (not question_id):
                raise ValueError
            
            question_instance = Question.objects.filter(pk=question_id).first()

            if not question_instance:
                raise ValueError
            
            question_answers = {}

            form_responses = FormResponse.objects.filter(
                question = question_id,
                response_datetime__date = response_date,
                department = department_id,
                vendor = vendor_id
            ).order_by('-response_datetime')

            response_list = []

            if form_responses.exists():
                for response in form_responses:
                    response_list.append({
                        "id": response.pk,
                        "submitted_by_id": response.submitted_by.pk,
                        "submitted_by_name": response.submitted_by.first_name + " " + response.submitted_by.last_name,
                        "remark": response.remark,
                        "response_datetime": response.response_datetime,
                        "answers": response.submitted_response.get("answers")
                    })

            question_answers["id"] = question_instance.pk
            question_answers["question_number"] = question_instance.question_number
            question_answers["question"] = question_instance.question
            question_answers["question_locale"] = question_instance.question_locale
            question_answers["is_response_multiple"] = question_instance.is_response_multiple
            question_answers["staff_category_id"] = question_instance.staff_category.pk
            question_answers["responses"] = response_list

        return JsonResponse({"question_answers": question_answers})
    
    except ValueError:
        return Response("Invalid request data", status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def create_sop_question_by_department(request):
    try:
        request_data = request.data
        
        required_keys = {
            "question_number", "question", "answers",
            "department_id", "staff_category_id", "vendor_id"
        }

        if not required_keys.issubset(request_data.keys()):
            raise ValueError
    
        question_no = request_data.get('question_number')
        question_text = request_data.get('question')
        question_text_locale = request_data.get('question_locale')
        is_response_multiple = request_data.get('is_response_multiple')
        answers = request_data.get('answers')
        department_id = request_data.get('department_id')
        staff_category_id = request_data.get('staff_category_id')
        vendor_id = request_data.get('vendor_id')
        
        if not all((question_no, question_text, answers, department_id, staff_category_id, vendor_id)):
            raise ValueError
    
        department_id = int(department_id)
        staff_category_id = int(staff_category_id)
        vendor_id = int(vendor_id)
    
        department_instance = Department.objects.filter(pk=department_id).first()
        staff_category_instance = CoreUserCategory.objects.filter(pk=staff_category_id).first()
        vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

        if not all((department_instance, staff_category_instance, vendor_instance)):
            raise ValueError
        
        question_instance = Question.objects.create(
            question_number = question_no,
            question = question_text,
            question_locale = question_text_locale,
            is_response_multiple = is_response_multiple,
            department = department_instance,
            staff_category = staff_category_instance,
            vendor = vendor_instance
        )
        
        for iterator in answers:
            answer_sequence_number = iterator.get('answer_sequence_number')
            answer_ui_element = iterator.get('ui_element')
            caption = iterator.get('caption')
            caption_locale = iterator.get('caption_locale')
            
            answer_instance = Answer.objects.create(
                question = question_instance,
                answer_sequence_number = answer_sequence_number,
                ui_element = answer_ui_element,
                caption = caption,
                caption_locale = caption_locale,
                vendor = vendor_instance
            )

        return Response(status = status.HTTP_201_CREATED)
    
    except ValueError:
        return Response("Invalid request data", status = status.HTTP_400_BAD_REQUEST)
    
    except IntegrityError as e:
        error_message = str(e)

        if 'duplicate key value violates unique constraint' in error_message:
            return Response("Question number already exists for this department", status = status.HTTP_409_CONFLICT)
        
        return Response(str(e), status = status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    except Exception as e:
        return Response(str(e), status = status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT'])
def update_sop_question(request):
    try:
        request_data = request.data
        
        if not request_data:
            raise ValueError
        
        required_keys = {
            "question_id",
            "question_number",
            "question",
            "is_response_multiple",
            "answers",
            "department_id",
            "staff_category_id",
            "vendor_id"
        }

        if not required_keys.issubset(request_data.keys()):
            raise ValueError
    
        question_id = request_data.get('question_id')
        question_no = request_data.get('question_number')
        question_text = request_data.get('question')
        question_text_locale = request_data.get('question_locale')
        is_response_multiple = request_data.get('is_response_multiple')
        answers = request_data.get('answers')
        department_id = request_data.get('department_id')
        staff_category_id = request_data.get('staff_category_id')
        vendor_id = request_data.get('vendor_id')
        
        if not all([question_id, question_no, question_text, answers, department_id, staff_category_id, vendor_id]):
            raise ValueError
    
        question_id = int(question_id)
        department_id = int(department_id)
        staff_category_id = int(staff_category_id)
        vendor_id = int(vendor_id)
    
        vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

        if not vendor_instance:
            raise ValueError

        question_instance = Question.objects.filter(pk=question_id, vendor=vendor_id).first()
        department_instance = Department.objects.filter(pk=department_id, vendor=vendor_id).first()
        staff_category_instance = CoreUserCategory.objects.filter(pk=staff_category_id, vendor=vendor_id).first()

        if not all((question_instance, department_instance, staff_category_instance)):
            raise ValueError

        question_instance.question_number = question_no
        question_instance.question = question_text
        question_instance.question_locale = question_text_locale
        question_instance.is_response_multiple = is_response_multiple
        question_instance.department = department_instance
        question_instance.staff_category = staff_category_instance

        question_instance.save()

        deleted_answer_ids = request_data.get("deleted_answer_ids")

        if deleted_answer_ids:
            for answer_id in deleted_answer_ids:
                answer_instance = Answer.objects.filter(pk=answer_id, vendor=vendor_id)
                answer_instance.delete()

        for answer in answers:
            if answer.get("id") == 0:
                answer_sequence_number = answer.get('answer_sequence_number')
                answer_ui_element = answer.get('ui_element')
                caption = answer.get('caption')
                caption_locale = answer.get('caption_locale')
                
                answer_instance = Answer.objects.create(
                    question = question_instance,
                    answer_sequence_number = answer_sequence_number,
                    ui_element = answer_ui_element,
                    caption = caption,
                    caption_locale = caption_locale,
                    vendor = vendor_instance
                )

        return Response(status = status.HTTP_200_OK)
    
    except ValueError:
        return Response("Invalid request data", status=status.HTTP_400_BAD_REQUEST)
    
    except IntegrityError as e:
        error_message = str(e)

        if 'duplicate key value violates unique constraint' in error_message:
            return Response("Question number already exists for this department", status=status.HTTP_400_BAD_REQUEST)
        
        return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    except Exception as e:
        return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
def delete_sop_question(request):
    try:
        question_id = request.GET.get('question_id')
        vendor_id = request.GET.get('vendor_id')

        if not all((question_id, vendor_id)):
            raise ValueError
    
        question_id = int(question_id)
        vendor_id = int(vendor_id)
    
        vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

        if not vendor_instance:
            raise ValueError
        
        question_instance = Question.objects.filter(pk=question_id, vendor=vendor_id).first()

        if not question_instance:
            raise ValueError

        question_instance.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)
    
    except ValueError:
        return Response("Invalid request data", status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
def submit_question_reponse(request):
    try:
        request_data = request.data
        
        if not request_data:
            raise ValueError
        
        required_keys = {"question_id", "answers", "submitted_by_id", "remark", "department_id", "vendor_id"}

        if not required_keys.issubset(request_data.keys()):
            raise ValueError

        question_id = request_data.get('question_id')
        answers = request_data.get('answers')
        core_user_id = request_data.get('submitted_by_id')
        remark = request_data.get('remark')
        department_id = request_data.get('department_id')
        vendor_id = request_data.get('vendor_id')
        
        if not all((question_id, answers, core_user_id, department_id, vendor_id)):
            raise ValueError
    
        question_id = int(question_id)
        core_user_id = int(core_user_id)
        department_id = int(department_id)
        vendor_id = int(vendor_id)
    
        question_instance = Question.objects.filter(pk=question_id).first()
        department_instance = Department.objects.filter(pk=department_id).first()
        core_user_instance = CoreUser.objects.filter(pk=core_user_id).first()
        vendor_instance = Vendor.objects.filter(pk=vendor_id).first()

        if not all((question_instance, department_instance, core_user_instance, vendor_instance)):
            raise ValueError
        
        for answer in answers:
            answer_id = answer.get('id')
            submitted_answer = answer.get('submitted_answer')
            
            if not ([answer_id, submitted_answer]):
                raise ValueError
            
            answer_id = int(answer_id)
            
            answer_instance = Answer.objects.filter(pk=answer_id).first()

            if not answer_instance:
                raise ValueError
            
            answer["answer_sequence_number"] = answer_instance.answer_sequence_number
            answer["ui_element"] = answer_instance.ui_element
            answer["caption"] = answer_instance.caption
            answer["caption_locale"] = answer_instance.caption_locale
            
        answers = {'answers': answers}
            
        form_response = FormResponse.objects.create(
            question = question_instance,
            submitted_response = answers,
            submitted_by = core_user_instance,
            remark = remark,
            department = department_instance,
            vendor = vendor_instance
        )

        return Response(status = status.HTTP_201_CREATED)
    
    except ValueError:
        return Response("Invalid request data", status = status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return Response(str(e), status = status.HTTP_500_INTERNAL_SERVER_ERROR)
