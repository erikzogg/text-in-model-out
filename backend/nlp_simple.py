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
            if is_semimodal(verb):
                continue

            the_object = get_the_object(verb)

            if not the_object:
                continue

            phrasal_verb = get_phrasal_verb(verb)  # hand in, set up, ...

            if not phrasal_verb:
                result.append({"type": "verb", "value": verb.lemma_ + " " + the_object.lemma_})
            else:
                result.append({"type": "verb", "value": verb.lemma_ + " " + phrasal_verb.lemma_ + " " + the_object.lemma_})

    return result


def is_semimodal(verb):
    has_xcomp = next((child for child in verb.children if (child.dep_ == "xcomp")), None)

    if has_xcomp:
        return True
    else:
        return False


def get_parent_verb(verb):
    return next((ancestor for ancestor in verb.ancestors if (verb in ancestor.children and verb.dep_ == "xcomp")), None)


def is_passive(verb):
    has_auxpass = next((child for child in verb.children if (child.dep_ == "auxpass")), None)
    has_nsubjpass = next((child for child in verb.children if (child.dep_ == "nsubjpass")), None)

    if has_auxpass and has_nsubjpass:
        return True
    else:
        return False


def get_the_object(verb):
    passive = is_passive(verb)
    parent_verb = get_parent_verb(verb)

    print(parent_verb)

    if parent_verb:
        passive = is_passive(parent_verb)

        if passive:
            the_object = next((child for child in parent_verb.children if (child.dep_ == "nsubjpass")), None)
        else:
            the_object = next((child for child in verb.children if (child.dep_ == "dobj")), None)

            if not the_object:
                the_object = next((child for child in parent_verb.children if (child.dep_ == "nsubj")), None)
    elif not passive:
        the_object = next((child for child in verb.children if (child.dep_ == "dobj")), None)
    else:
        the_object = next((child for child in verb.children if (child.dep_ == "nsubjpass")), None)

    return the_object


def get_phrasal_verb(verb):
    return next((child for child in verb.children if (child.dep_ == "prt")), None)
