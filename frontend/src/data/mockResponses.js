// Réponses simulées utilisées tant que le backend n'est pas branché.
// À supprimer quand /api/chat renverra de vraies réponses.

export const SUGGESTIONS = [
  'Quels sont les horaires de la scolarité ?',
  'Comment contacter le service scolarité ?',
  'Quelles formations propose l’ESIC ?',
  'Quand sont les prochaines vacances ?',
  'Comment obtenir un certificat de scolarité ?',
  'Quelles sont les règles de vie du campus ?',
]

const MOCK_KB = [
  {
    keywords: ['horaire', 'ouvert', 'ouverture'],
    answer:
      'Le service scolarité est ouvert du lundi au vendredi, de 9h à 17h.',
    source: 'Guide de l’étudiant',
  },
  {
    keywords: ['contact', 'contacter', 'mail', 'téléphone', 'telephone'],
    answer:
      'Vous pouvez joindre la scolarité par e-mail à scolarite@esic.fr ou passer directement au bureau du rez-de-chaussée.',
    source: 'Annuaire des contacts',
  },
  {
    keywords: ['formation', 'formations', 'programme', 'cursus'],
    answer:
      'L’ESIC propose notamment des formations en Data Science, Cybersécurité et Développement. Chaque parcours est accessible en initial ou en alternance.',
    source: 'Catalogue des formations',
  },
  {
    keywords: ['vacances', 'congé', 'conge', 'calendrier', 'examen'],
    answer:
      'Le calendrier académique (vacances, examens, soutenances) est disponible sur l’ENT. Les vacances de la Toussaint commencent fin octobre.',
    source: 'Calendrier académique',
  },
  {
    keywords: ['certificat', 'attestation', 'relevé', 'releve'],
    answer:
      'Le certificat de scolarité est téléchargeable depuis votre espace ENT, rubrique « Mes documents ». En cas de problème, contactez la scolarité.',
    source: 'Procédures administratives',
  },
  {
    keywords: ['règle', 'regle', 'règlement', 'reglement', 'vie'],
    answer:
      'Le règlement intérieur précise les droits et devoirs des étudiants (assiduité, respect des locaux, sanctions). Il est consultable sur l’ENT.',
    source: 'Règlement intérieur',
  },
  {
    keywords: ['bonjour', 'salut', 'hello', 'coucou'],
    answer: 'Bonjour ! Posez-moi votre question sur le campus, je suis là pour vous aider.',
    source: null,
  },
]

export function getMockAnswer(question) {
  const q = question.toLowerCase()
  const match = MOCK_KB.find((item) => item.keywords.some((k) => q.includes(k)))

  if (match) {
    return { answer: match.answer, source: match.source }
  }
  return {
    answer:
      'Je n’ai pas encore de réponse fiable à cette question. Vous pouvez reformuler ou contacter directement le service scolarité.',
    source: null,
  }
}
