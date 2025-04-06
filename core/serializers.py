from rest_framework import serializers
from .models import User, Panelist, Campaign, Feedback, Interest, Announcer, Question, Section, Form

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role']

class CampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = Campaign
        fields = '__all__'

class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = '__all__'
class InterestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interest
        fields = ['id', 'name']

class PanelistSerializer(serializers.ModelSerializer):
    interests = serializers.PrimaryKeyRelatedField(queryset=Interest.objects.all(), many=True)

    class Meta:
        model = Panelist
        fields = ['id', 'full_name', 'email', 'phone_number', 'interests']

class AnnouncerSerializer(serializers.ModelSerializer):
    industry = serializers.PrimaryKeyRelatedField(queryset=Interest.objects.all())

    class Meta:
        model = Announcer
        fields = ['id', 'company_name', 'email', 'phone_number', 'industry']


# core/serializers.py
from rest_framework import serializers
from .models import Question

class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ['id', 'form', 'section', 'text', 'question_type', 'is_required', 'order', 'is_active']
