import spacy
import lemminflect
from spacy import displacy
from pathlib import Path

determiners = ['a', 'an', 'the']


def parse(text):
    output = {"startevent": "", "activities": [], "endevent": ""}

    activities = []

    nlp = spacy.load("en_core_web_sm")
    nlp.add_pipe("merge_noun_chunks")

    doc = nlp(text)

    for index, sent in enumerate(doc.sents):
        for token in sent:
            # First iteration: Detect startevent
            if token.pos_ == "VERB" and output["startevent"] == "":
                for child in token.children:
                    if child.dep_ == "nsubjpass" or child.dep_ == "dobj":
                        startevent = child.text + " " + token._.inflect('VBN')
                        startevent = " ".join([word for word in startevent.split() if word.lower() not in determiners])

                        output["startevent"] = startevent
            # Remaining iterations: Detect activities
            elif token.pos_ == "VERB":
                if len([child for child in token.children if (child.pos_ == "VERB" and child.dep_ == "xcomp")]) > 0:
                    # Skip semi-modal verbs (e.g. needs to...)
                    continue

                activity = token.lemma_

                for child in token.children:
                    # Find phrasal verbs
                    if child.pos_ == "ADP":
                        noun = next((noun for noun in child.children if (noun.pos_ == "NOUN")), None)

                        activity = activity + " " + child.lemma_

                        if noun:
                            activity = activity + " " + noun.text

                for child in token.children:
                    if child.dep_ == "nsubjpass" or child.dep_ == "dobj":
                        activity = activity + " " + child.text

                # Find subject from semi-modal-verb
                for parent in token.ancestors:
                    if token in parent.children and token.dep_ == "xcomp":
                        subject = next(subject for subject in parent.children if (subject.dep_ == "nsubj"))
                        activity = activity + " " + subject.text

                activity = " ".join([word for word in activity.split() if word.lower() not in determiners])

                output["activities"].append(activity)

    svg = displacy.render(doc, style="dep")

    output_path = Path("./dependency_plot.svg")
    output_path.open("w", encoding="utf-8").write(svg)

    return output
