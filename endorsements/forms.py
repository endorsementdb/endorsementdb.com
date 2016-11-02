from django import forms

from endorsements.models import Candidate, Endorsement, Source, Position, \
                                Tag, Event


class Html5DateInput(forms.DateInput):
    input_type = 'date'


class SourceForm(forms.ModelForm):
    class Meta:
        model = Source
        exclude = ('name',)
        widgets = {
            'date': Html5DateInput(),
        }


class PersonalTagForm(forms.Form):
    tag = forms.ModelChoiceField(
        Tag.objects.filter(is_personal=True)
    )


class OrganizationTagForm(forms.Form):
    tag = forms.ModelChoiceField(
        Tag.objects.filter(is_personal=False)
    )


class TagFilterForm(forms.Form):
    filter_tags_show = forms.ModelMultipleChoiceField(
        Tag.objects.all(), required=False
    )
    filter_tags_hide = forms.ModelMultipleChoiceField(
        Tag.objects.all(), required=False
    )


class EndorsementForm(forms.Form):
    position = forms.ModelChoiceField(Position.objects.all())
    quote = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2}),
        required=False,
    )
    context = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 1}),
        required=False,
    )
    date = forms.DateField(widget=Html5DateInput)
    source_url = forms.URLField()
    source_name = forms.CharField()
    event = forms.ModelChoiceField(Event.objects.all(), required=False)
