# Instructions for raters

There are **73 items** in `sheet.md`. Please score every one in `ratings.csv`.

Each item shows the true EC number from the database; you are not told which system wrote which text. Judge each item on the chemistry in front of you.

## Scale

- **mechanism_correct** — Is the mechanism correct for the reaction as recorded (the SMILES, left to right)? (2 = correct; 1 = partly correct or too vague to be wrong; 0 = incorrect: wrong bond changes, wrong direction, or a mechanism of a different kind of reaction). Anchor: a dehydrogenase text that transfers the hydride to the wrong carbon is 0; one that names no residues but gets the hydride transfer right is 2.

- **enzyme_plausible** — Is the proposed enzyme right for this reaction? If the true EC is shown, judge against it. (2 = same EC4 as the true one, or the reaction is clearly that enzyme's; 1 = right sub-subclass, different enzyme; 0 = wrong kind of enzyme)

- **contradicts_reaction** — Does the text contradict the reaction as recorded or basic chemistry? (0 = no; 1 = a minor slip, e.g. a miscounted H; 2 = a substantive error: an invented participant or co-product, the wrong atoms or bonds, the wrong direction). Details you cannot check are NOT counted here.

- **unverifiable_detail** — Does the text add specific details found neither in the reaction nor in the mechanism reference shown (residue numbers, metals, named intermediates)? (0 = none; 1 = one or two; 2 = many, or details copied from a different enzyme or substrate in the reference)

- **useful** — Would this help a biochemist understand the prediction? (2 = yes, 1 = somewhat, 0 = no)


`notes`: anything wrong that the scores do not capture, especially invented cofactors, wrong bond changes, or mechanisms taken from a different substrate.
