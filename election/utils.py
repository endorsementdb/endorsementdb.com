def predict_winner(clinton_stat, trump_stat, threshold, is_percent=False):
    difference = clinton_stat - trump_stat
    abs_difference = abs(difference)
    if difference == 0:
        color = 'grey'
        basic_class = ''
        winner = None
    else:
        if difference >= 0:
            color = 'blue'
            winner = 'clinton'
        else:
            color = 'red'
            winner = 'trump'

        max_stat = max(clinton_stat, trump_stat)
        if abs_difference > threshold or abs_difference == max_stat:
            basic_class = ''
        else:
            basic_class = ' basic'

    return {
        'color': color,
        'winner': winner,
        'basic': basic_class,
        'diff': abs(difference),
        'clinton': clinton_stat,
        'trump': trump_stat,
        'suffix': '%' if is_percent else '',
    }
