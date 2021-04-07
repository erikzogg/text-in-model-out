import spacy
from spacy import displacy
from pathlib import Path


def parse(text):
    activities = []

    nlp = spacy.load("en_core_web_sm")
    doc = nlp(text)

    for sent in doc.sents:
        for token in sent:
            if token.pos_ == "VERB":
                activity = ""

                for child in token.children:
                    if child.pos_ == "ADP":
                        activity = token.lemma_ + " " + child.lemma_

                if activity == "":
                    activity = token.lemma_

                activities.append(activity)

    svg = displacy.render(doc, style="dep")

    output_path = Path("./dependency_plot.svg")
    output_path.open("w", encoding="utf-8").write(svg)

    return activities
