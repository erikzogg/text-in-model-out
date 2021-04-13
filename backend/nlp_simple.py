import spacy
import lemminflect
from spacy import displacy
from spacy.lang.en.stop_words import STOP_WORDS
from pathlib import Path


def parse(text):
    nlp = spacy.load("en_core_web_trf")
    nlp.add_pipe("merge_noun_chunks")

    doc = nlp(text)

    svg = displacy.render(doc, style="dep")

    output_path = Path("./dependency_plot.svg")
    output_path.open("w", encoding="utf-8").write(svg)

    elements = []

    for sent in doc.sents:
        verbs = [token for token in sent if token.pos_ == "VERB"]

        for verb in verbs:
            condition = get_condition(verb)

            if condition:
                elements.append({"type": "condition", "condition": condition})
                continue

            if is_semimodal(verb):
                continue

            the_object = get_the_object(verb)

            if not the_object:
                continue

            elements.append({"type": "verb", "object": the_object, "verb": verb})

    return parse_elements(elements)


def get_condition(verb):
    passive = is_passive(verb)
    parent_verb = get_parent_verb(verb)

    mark = next((child for child in verb.children if (child.dep_ == "mark" and child.text.lower() in ["if"])), None)

    if mark:
        if passive:
            nsubjpass = next((child for child in verb.children if (child.dep_ == "nsubjpass")), None)

            return nsubjpass.text + "  " + verb.text + "?"
        else:
            nsubj = next((child for child in verb.children if (child.dep_ == "nsubj")), None)
            aux = next((child for child in verb.children if (child.dep_ == "aux")), None)
            negative = next((child for child in verb.children if (child.dep_ == "neg" and child in verb.lefts)), None)
            dobj = next((child for child in verb.children if (child.dep_ == "dobj")), None)

            if not dobj:
                neighbor_children = list(verb.rights)
                condition_text = []

                while neighbor_children:
                    for child in neighbor_children:
                        condition_text.append(child.text)
                        neighbor_children.remove(child)
                        if child.rights:
                            for subchild in child.rights:
                                neighbor_children.append(subchild)

                dobj = " ".join(condition_text)
            else:
                dobj = dobj.text

            conditional_label = nsubj.text

            if aux:
                conditional_label += " " + aux.text

            if negative:
                conditional_label += " " + negative.text

            conditional_label += " " + verb.text + " " + dobj + "?"

            return conditional_label

    prep = next((child for child in verb.children if (child.dep_ == "prep")), None)

    if prep:
        pobj = next((child for child in prep.children if (child.dep_ == "pobj")), None)

        if pobj:
            conditional_conj = prep.lemma_ + " " + pobj.lemma_

            if conditional_conj.lower() in ["for the case", "in case", "in the case"]:
                return True

    return False


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


def get_actor(verb):
    passive = is_passive(verb)
    parent_verb = get_parent_verb(verb)

    if parent_verb:
        agent = next((child for child in verb.children if (child.dep_ == "agent")), None)

        if agent:
            actor = next((child for child in agent.children if (child.dep_ == "pobj")), None)
        else:
            actor = next((child for child in parent_verb.children if (child.dep_ == "nsubj")), None)
    elif not passive:
        actor = next((child for child in verb.children if (child.dep_ == "nsubj")), None)
    else:
        agent = next((child for child in verb.children if (child.dep_ == "agent")), None)

        if agent:
            actor = next((child for child in agent.children if (child.dep_ == "pobj")), None)
        else:
            actor = None

    return actor


def parse_elements(elements):
    result = []

    current_actor = "Default"

    for element in elements:
        if element["type"] == "verb":
            the_object = element['object']
            verb = element['verb']
            phrasal_verb = get_phrasal_verb(verb)  # hand in, set up, ...

            the_object = " ".join([word for word in the_object.lemma_.split() if word.lower() not in STOP_WORDS])

            actor = get_actor(verb)

            if actor:
                current_actor = actor.lemma_

            actor = " ".join([word for word in current_actor.split() if word.lower() not in STOP_WORDS])

            if element == elements[0]:
                if not phrasal_verb:
                    result.append({"type": "start_event", "value": the_object + " " + verb._.inflect("VBN"), "actor": actor})
                else:
                    result.append({"type": "start_event", "value": the_object + " " + verb._.inflect("VBN") + " " + phrasal_verb.lemma_, "actor": actor})
            else:
                if not phrasal_verb:
                    result.append({"type": "activity", "value": verb.lemma_ + " " + the_object, "actor": actor})
                else:
                    result.append({"type": "activity", "value": verb.lemma_ + " " + phrasal_verb.lemma_ + " " + the_object, "actor": actor})

            if element == elements[-1]:
                if not phrasal_verb:
                    result.append({"type": "end_event", "value": the_object + " " + verb._.inflect("VBN"), "actor": actor})
                else:
                    result.append({"type": "end_event", "value": the_object + " " + verb._.inflect("VBN") + " " + phrasal_verb.lemma_, "actor": actor})
        elif element["type"] == "condition":
            condition = element["condition"]

            condition = " ".join([word for word in condition.split() if word.lower() not in ["a", "an", "the"]])
            result.append({"type": "xor_start", "value": condition, "actor": actor})

    return result
