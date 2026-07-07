from rest_framework import serializers
from my_psc_kerala.models import UserPerformance, Question

class UserPerformanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPerformance
        fields = ['id', 'question', 'is_correct', 'attempted_date']
        read_only_fields = ['id', 'is_correct', 'attempted_date']

class MCQAttemptSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    selected_option = serializers.ChoiceField(choices=['A', 'B', 'C', 'D'])
