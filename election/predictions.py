import collections


class PredictionModel:
    @classmethod
    def apply_model(cls, state_pks, endorser_pks):
        model_pks = set()
        for key in cls.keys:
            model_pks |= endorser_pks[key]

        state_model_pks = state_pks & model_pks
        clinton_pks = set()
        for clinton_key in cls.clinton_keys:
            clinton_pks |= endorser_pks[clinton_key]
        clinton_count = len(state_model_pks & clinton_pks)

        trump_pks = set()
        for trump_key in cls.trump_keys:
            trump_pks |= endorser_pks[trump_key]
        trump_count = len(state_model_pks & trump_pks)

        return {
            'clinton': clinton_count,
            'trump': trump_count,
        }


class PartyModel(PredictionModel):
    clinton_keys = ['democrat']
    trump_keys = ['republican']
    threshold = 1


class SenatePartyModel(PartyModel):
    keys = ['senate']
    name = 'Senate - party'


class HousePartyModel(PartyModel):
    keys = ['house']
    name = 'House - party'


class CongressPartyModel(PartyModel):
    keys = ['house', 'senate']
    name = 'Congress - party'


class EndorsementModel(PredictionModel):
    clinton_keys = ['clinton']
    trump_keys = ['trump']
    threshold = 1


class SenateEndorsementModel(EndorsementModel):
    keys = ['senate']
    name = 'Senate - endorsed'


class HouseEndorsementModel(EndorsementModel):
    keys = ['house']
    name = 'House - endorsed'


class CongressEndorsementModel(EndorsementModel):
    keys = ['house', 'senate']
    name = 'Congress - endorsed'


class CongressUnlessTiedThenHouseModel:
    name = 'Congress endorsements (unless tied; then, House endorsements)'
    threshold = 1

    @classmethod
    def apply_model(cls, state_pks, endorser_pks):
        congress_counts = CongressEndorsementModel.apply_model(
            state_pks,
            endorser_pks
        )
        if congress_counts['clinton'] == congress_counts['trump']:
            return HouseEndorsementModel.apply_model(
                state_pks,
                endorser_pks
            )
        else:
            return congress_counts



class SenateUnlessTiedModel:
    name = 'Senate endorsements (unless tied; then, House endorsements)'
    threshold = 1

    @classmethod
    def apply_model(cls, state_pks, endorser_pks):
        senate_counts = SenateEndorsementModel.apply_model(
            state_pks,
            endorser_pks
        )
        if senate_counts['clinton'] == senate_counts['trump']:
            return HouseEndorsementModel.apply_model(
                state_pks,
                endorser_pks
            )
        else:
            return senate_counts


class HouseUnlessTiedModel:
    name = 'House endorsements (unless tied; then, Senate endorsements)'
    threshold = 1

    @classmethod
    def apply_model(cls, state_pks, endorser_pks):
        house_counts = HouseEndorsementModel.apply_model(
            state_pks,
            endorser_pks
        )
        if house_counts['clinton'] == house_counts['trump']:
            return SenateEndorsementModel.apply_model(
                state_pks,
                endorser_pks
            )
        else:
            return house_counts


class SenateIfUnanimousModel:
    name = (
        'House (unless tied, or Senate is unanimous; then, Senate endorsements)'
    )
    threshold = 1

    @classmethod
    def apply_model(cls, state_pks, endorser_pks):
        senate_counts = SenateEndorsementModel.apply_model(
                state_pks,
                endorser_pks
            )
        house_counts = HouseEndorsementModel.apply_model(
            state_pks,
            endorser_pks
        )
        if (
                senate_counts['clinton'] == 2 or
                senate_counts['trump'] == 2 or
                house_counts['clinton'] == house_counts['trump']
        ):
            return senate_counts
        else:
            return house_counts


class NewspaperEndorsementModel(PredictionModel):
    keys = ['newspaper']
    clinton_keys = ['clinton']
    trump_keys = ['trump']
    threshold = 1
    name = 'Newspaper endorsements'


class TrumpNewspaperEndorsementModel(PredictionModel):
    threshold = 1
    name = 'Newspaper endorsements for Trump'

    @classmethod
    def apply_model(cls, state_pks, endorser_pks):
        """Award Trump every state for which Clinton did not get any
        endorsements."""
        counts = NewspaperEndorsementModel.apply_model(state_pks, endorser_pks)
        if counts['trump']:
            counts['clinton'] = 0
        elif counts['clinton'] == 0:
            counts['trump'] = 2

        return counts


MODELS = collections.OrderedDict()
MODELS['Congress - by party'] = [
    SenatePartyModel,
    HousePartyModel,  # not as fun as it sounds
    CongressPartyModel,
]
MODELS['Congress - by endorsements'] = [
    SenateEndorsementModel,
    HouseEndorsementModel,
    CongressEndorsementModel,
]
MODELS['Congress - combined endorsement models'] = [
    #SenateUnlessTiedModel,
    CongressUnlessTiedThenHouseModel,
    HouseUnlessTiedModel,
    SenateIfUnanimousModel,
]
MODELS['Newspaper endorsements'] = [
    NewspaperEndorsementModel,
    TrumpNewspaperEndorsementModel,
]
