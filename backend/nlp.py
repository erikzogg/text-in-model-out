import spacy
import lemminflect
from spacy import displacy
from pathlib import Path

determiners = ['a', 'an', 'the']


def parse(text):
    output = {"startevent": "", "activities": [], "endevent": ""}
    result = []

    nlp = spacy.load("en_core_web_sm")
    nlp.add_pipe("merge_noun_chunks")

    doc = nlp(text)

    sentences_number = len(list(doc.sents))
    current_role = "Default"

    for index, sent in enumerate(doc.sents, 1):
        for token in sent:
            # Detect role
            if token.pos_ == "VERB":
                role = next((child for child in token.children if (child.dep_ == "nsubj")), None)
                if role:
                    not_suitable = next((child for child in token.children if (child.dep_ in ["mark", "xcomp", "ccomp"])), None)
                    if not not_suitable:
                        rolename = role.text
                        rolename = " ".join([word for word in rolename.split() if word.lower() not in determiners])

                        current_role = rolename

            # First iteration: Detect startevent
            if token.pos_ == "VERB" and output["startevent"] == "":
                the_object = next((child for child in token.children if (child.dep_ == "nsubjpass" or child.dep_ == "dobj")), None)
                phrasal_verb = next((child for child in token.children if (child.pos_ == "ADP" and child.dep_ == "prt")), None)

                if not the_object and phrasal_verb:
                    the_object = next((child for child in phrasal_verb.children if (child.dep_ == "pobj")), None)

                startevent = None

                if the_object:
                    startevent = the_object.text + " " + token._.inflect('VBN')

                if the_object and phrasal_verb:
                    startevent = the_object.text + " " + token._.inflect('VBN') + " " + phrasal_verb.text

                if startevent:
                    startevent = " ".join([word for word in startevent.split() if word.lower() not in determiners])

                    output["startevent"] = startevent
                    result.append({'type': 'startevent', 'value': startevent, 'role': current_role})
            # Remaining iterations: Detect activities
            elif token.pos_ == "VERB":
                # Detect condition
                has_mark = next((child for child in token.children if (child.pos_ == "ADV")), None)
                if has_mark:
                    continue

                if len([child for child in token.children if (child.pos_ == "VERB" and child.dep_ == "xcomp")]) > 0:
                    # Skip semi-modal verbs (e.g. needs to...)
                    continue

                the_object = next((child for child in token.children if (child.dep_ == "nsubjpass" or child.dep_ == "dobj")), None)
                phrasal_verb = next((child for child in token.children if (child.pos_ == "ADP" and child.dep_ == "prt")), None)

                if not the_object and phrasal_verb:
                    the_object = next((child for child in phrasal_verb.children if (child.dep_ == "pobj")), None)

                # Search object in case of a semi-modal verb
                if not the_object:
                    for parent in token.ancestors:
                        if token in parent.children and token.dep_ == "xcomp":
                            the_object = next(subject for subject in parent.children if (subject.dep_ == "nsubj"))

                activity = None

                if the_object:
                    activity = token.lemma_

                    if phrasal_verb:
                        activity = activity + " " + phrasal_verb.lemma_

                    activity = activity + " " + the_object.text

                if activity:
                    activity = " ".join([word for word in activity.split() if word.lower() not in determiners])

                    output["activities"].append(activity)
                    result.append({'type': 'activity', 'value': activity, 'role': current_role})

            # End event detection
            if index == sentences_number:
                if token.pos_ == "VERB":
                    # Make sure that only the last verb in a sentence is considered
                    if len([child for child in token.children if (child.pos_ == "VERB")]) == 0:
                        the_object = next((child for child in token.children if (child.dep_ == "nsubjpass" or child.dep_ == "dobj")), None)
                        phrasal_verb = next((child for child in token.children if (child.pos_ == "ADP" and child.dep_ == "prt")), None)

                        if not the_object and phrasal_verb:
                            the_object = next((child for child in phrasal_verb.children if (child.dep_ == "pobj")), None)

                        if not the_object:
                            for parent in token.ancestors:
                                if token in parent.children and token.dep_ == "xcomp":
                                    the_object = next(subject for subject in parent.children if (subject.dep_ == "nsubj"))

                        endevent = None

                        if the_object:
                            endevent = the_object.text + " " + token._.inflect('VBN')

                        if the_object and phrasal_verb:
                            endevent = the_object.text + " " + token._.inflect('VBN') + " " + phrasal_verb.text

                        if endevent:
                            endevent = " ".join([word for word in endevent.split() if word.lower() not in determiners])

                            output["endevent"] = endevent

    if not output["endevent"] == "":
        result.append({'type': 'endevent', 'value': output["endevent"], 'role': current_role})

    svg = displacy.render(doc, style="dep")

    output_path = Path("./dependency_plot.svg")
    output_path.open("w", encoding="utf-8").write(svg)

    return result
