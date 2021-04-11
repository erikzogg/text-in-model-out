import spacy
import lemminflect
from spacy import displacy
from pathlib import Path


def parse(text):
    nlp = spacy.load("en_core_web_trf")
    nlp.add_pipe("merge_noun_chunks")

    doc = nlp(text)

    svg = displacy.render(doc, style="dep")

    output_path = Path("./dependency_plot.svg")
    output_path.open("w", encoding="utf-8").write(svg)

    result = []

    for sent in doc.sents:
        verbs = [token for token in sent if token.pos_ == "VERB"]

        for verb in verbs:
            phrasal_verb = next((child for child in verb.children if (child.dep_ == "prt")), None)  # hand in, set up, ...

            if not phrasal_verb:
                result.append({"type": "verb", "value": verb.lemma_})
            else:
                result.append({"type": "verb", "value": verb.lemma_ + " " + phrasal_verb.lemma_})

    return result
