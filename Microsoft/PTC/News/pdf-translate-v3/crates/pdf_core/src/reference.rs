/// Indirect-object identifier `(object number, generation number)`.
#[derive(Debug, Clone, Copy, Eq, PartialEq, Hash, Ord, PartialOrd)]
#[cfg_attr(
    feature = "serde",
    derive(serde::Serialize, serde::Deserialize)
)]
pub struct ObjectId {
    pub number: u32,
    pub generation: u16,
}

impl ObjectId {
    pub const fn new(number: u32, generation: u16) -> Self {
        Self { number, generation }
    }

    pub const fn root_candidate() -> Self {
        Self {
            number: 1,
            generation: 0,
        }
    }
}

impl std::fmt::Display for ObjectId {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{} {} R", self.number, self.generation)
    }
}

/// `n g R` indirect reference. Distinct from `ObjectId` so that
/// `PdfObject::Reference(ObjectRef)` reads cleanly in match arms.
#[derive(Debug, Clone, Copy, Eq, PartialEq, Hash, Ord, PartialOrd)]
#[cfg_attr(
    feature = "serde",
    derive(serde::Serialize, serde::Deserialize)
)]
pub struct ObjectRef {
    pub id: ObjectId,
}

impl ObjectRef {
    pub const fn new(number: u32, generation: u16) -> Self {
        Self {
            id: ObjectId::new(number, generation),
        }
    }
}

impl From<ObjectId> for ObjectRef {
    fn from(id: ObjectId) -> Self {
        Self { id }
    }
}
