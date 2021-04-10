import spacy
import lemminflect
from spacy import displacy
from pathlib import Path

determiners = ['a', 'an', 'the']


def parse(text):
    output = {"startevent": "", "activities": [], "endevent": ""}

    nlp = spacy.load("en_core_web_sm")
    nlp.add_pipe("merge_noun_chunks")

    doc = nlp(text)

    sentences_number = len(list(doc.sents))

    for index, sent in enumerate(doc.sents, 1):
        for token in sent:
            # First iteration: Detect startevent
            if token.pos_ == "VERB" and output["startevent"] == "":
                the_object = next((child for child in token.children if (child.dep_ == "nsubjpass" or child.dep_ == "dobj")), None)
                phrasal_verb = next((child for child in token.children if (child.pos_ == "ADP")), None)

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
            # Remaining iterations: Detect activities
            elif token.pos_ == "VERB":
                if len([child for child in token.children if (child.pos_ == "VERB" and child.dep_ == "xcomp")]) > 0:
                    # Skip semi-modal verbs (e.g. needs to...)
                    continue

                the_object = next((child for child in token.children if (child.dep_ == "nsubjpass" or child.dep_ == "dobj")), None)
                phrasal_verb = next((child for child in token.children if (child.pos_ == "ADP")), None)

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

            # End event detection
            if index == sentences_number:
                if token.pos_ == "VERB":
                    the_object = next((child for child in token.children if (child.dep_ == "nsubjpass" or child.dep_ == "dobj")), None)
                    phrasal_verb = next((child for child in token.children if (child.pos_ == "ADP")), None)

                    if not the_object and phrasal_verb:
                        the_object = next((child for child in phrasal_verb.children if (child.dep_ == "pobj")), None)

                    endevent = None

                    if the_object:
                        endevent = the_object.text + " " + token._.inflect('VBN')

                    if the_object and phrasal_verb:
                        endevent = the_object.text + " " + token._.inflect('VBN') + " " + phrasal_verb.text

                    if endevent:
                        endevent = " ".join([word for word in endevent.split() if word.lower() not in determiners])

                        output["endevent"] = endevent

    svg = displacy.render(doc, style="dep")

    output_path = Path("./dependency_plot.svg")
    output_path.open("w", encoding="utf-8").write(svg)

    return output
