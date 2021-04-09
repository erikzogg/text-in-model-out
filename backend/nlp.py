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

                        if startevent.split(' ')[0].lower() in determiners:
                            startevent = " ".join(startevent.split(' ')[1:])

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
                        activity = token.lemma_ + " " + child.lemma_

                output["activities"].append(activity)

    svg = displacy.render(doc, style="dep")

    output_path = Path("./dependency_plot.svg")
    output_path.open("w", encoding="utf-8").write(svg)

    return output
