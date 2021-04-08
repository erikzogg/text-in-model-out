import spacy
import lemminflect
from spacy import displacy
from pathlib import Path

determiners = ['a', 'an', 'the']


def parse(text):
    activities = []

    nlp = spacy.load("en_core_web_sm")
    nlp.add_pipe("merge_noun_chunks")

    doc = nlp(text)

    get_startevent(doc)

    for index, sent in enumerate(doc.sents):
        for token in sent:
            if token.pos_ == "VERB":
                if len([child for child in token.children if (child.pos_ == "VERB" and child.dep_ == "xcomp")]) > 0:
                    # Skip semi-modal verbs
                    continue

                activity = ""

                for child in token.children:
                    # Find phrasal verbs
                    if child.pos_ == "ADP":
                        activity = token.lemma_ + " " + child.lemma_

                if activity == "":
                    activity = token.lemma_

                activities.append(activity)

    svg = displacy.render(doc, style="dep")

    output_path = Path("./dependency_plot.svg")
    output_path.open("w", encoding="utf-8").write(svg)

    return activities


def get_startevent(doc):
    startevent = ""

    for index, sentence in enumerate(doc.sents):
        if index == 0:
            for token in sentence:
                if token.pos_ == "VERB":
                    for child in token.children:
                        if child.dep_ == "nsubjpass" or child.dep_ == "dobj":
                            startevent = child.text + " " + token._.inflect('VBN')

                            if startevent.split(' ')[0] in determiners:
                                startevent = " ".join(startevent.split(' ')[1:])

                            return startevent
        else:
            break

    return startevent
